# Feature Request: Semantic Cache for RAG Pipeline

## Overview

Upgrade the existing exact-match cache (`QueryCache`) to include a **semantic cache** that can match queries based on semantic similarity, not just exact text matches. This will significantly improve cache hit rates by returning cached answers for semantically similar queries, even when worded differently.

## Motivation

Currently, the RAG pipeline uses an exact-match cache (`query_cache.get()` / `query_cache.set()`) that only matches queries with identical text. This means:

- "What is Litecoin?" and "Tell me about Litecoin" are treated as different queries
- Follow-up questions with slight rephrasing miss the cache
- Cache hit rates are lower than optimal, leading to unnecessary LLM API calls

A semantic cache will:
- **Increase cache hit rates** from ~20-30% to **60-90%** on real traffic
- **Reduce LLM API costs** by avoiding redundant queries
- **Improve response latency** for semantically similar queries
- **Better handle follow-up questions** that rephrase previous queries

## Technical Approach

### Architecture

Implement a **multi-layer caching strategy** with the following hierarchy:

1. **Suggested Question Cache** (existing, Redis-based) - Pre-computed answers for UI suggested questions
   - Checked FIRST in API endpoint (before RAG pipeline)
   - Only for empty chat history
   - Exact match, no chat history context
   - **This cache will remain unchanged and continue to work independently**

2. **Semantic Cache** (new, in-memory) - First layer in RAG pipeline, matches by embedding similarity
   - Checked inside RAG pipeline after Suggested Question Cache miss
   - Includes chat history context
   - Uses cosine similarity with configurable threshold

3. **Exact Cache** (existing, in-memory) - Second layer in RAG pipeline, matches by exact text
   - Checked after Semantic Cache miss
   - Includes chat history context
   - Fast exact-match fallback

4. **Embedding Cache** (existing) - Optional, for retriever-level deduplication

### Cache Flow

```
User Query
    ↓
[Suggested Question Cache] (Redis, exact match, empty history only)
    ├─ Hit → Return cached answer
    └─ Miss → Continue to RAG Pipeline
         ↓
    [Semantic Cache] (in-memory, similarity match, includes history)
         ├─ Hit → Return cached answer
         └─ Miss → Continue
              ↓
         [Exact Cache] (in-memory, exact match, includes history)
              ├─ Hit → Return cached answer
              └─ Miss → Generate via LLM
                   ↓
              Store in both Semantic Cache + Exact Cache
```

### Implementation Strategy

#### Core Components

**SemanticCache Class** (`backend/cache_utils.py`):
- Uses `GoogleGenerativeAIEmbeddings` (same model family as LLM) for consistency
- Stores query embeddings with cached answers and sources
- Uses cosine similarity with configurable threshold (default: 0.93)
- Includes chat history context in semantic matching
- Implements LRU eviction and TTL-based expiration

**Integration Points** (`backend/rag_pipeline.py`):
- `aquery()` method: Check semantic cache first, then exact cache
- `astream_query()` method: Same two-layer approach with streaming support
- Cache results in both semantic and exact caches after generation

### Key Features

| Feature | Benefit |
|---------|---------|
| Embedding-based matching | Captures semantic meaning, not just text |
| Chat history context | Follow-up questions match better |
| Cosine similarity + threshold | Avoids false positives |
| TTL + LRU eviction | Memory safe and efficient |
| Fast in-memory lookup | < 5ms lookup time |
| Monitoring integration | Track hit rates via Prometheus |

## Implementation Details

### Step 1: Add SemanticCache Class

**File**: `backend/cache_utils.py`

```python
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import numpy as np

class SemanticCache:
    """
    Semantic cache that stores (query → answer + sources) using embedding similarity.
    Uses Google Gemini embeddings (same as your vector store) for consistency.
    """
    
    def __init__(self, 
                 threshold: float = 0.92,        # Tune this: 0.90–0.95 works well
                 max_size: int = 2000,
                 ttl_seconds: int = 3600 * 24):  # 24h default, might go with 48 hours.
        self.threshold = threshold
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # Cache structure: list of dicts (we'll use LRU manually)
        self.entries: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        
        # Shared embedding model (cached)
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=google_api_key  # already loaded globally
        )

    def _embed(self, text: str) -> np.ndarray:
        """Embed a single text (with caching via lru_cache for same queries in one process)"""
        return np.array(self.embeddings.embed_query(text))

    def _normalize(self, query: str) -> str:
        return query.strip().lower()

    def get(self, query: str, chat_history: List[Tuple[str, str]] = None) -> Optional[Tuple[str, List[Document]]]:
        """
        Return cached (answer, sources) if semantic similarity > threshold.
        Includes recent chat history in the semantic context.
        """
        normalized = self._normalize(query)
        search_text = self._build_search_text(normalized, chat_history or [])
        
        query_vec = self._embed(search_text).reshape(1, -1)

        with self._lock:
            now = time.time()
            best_match = None
            best_score = 0.0

            for entry in self.entries:
                if now - entry["timestamp"] > self.ttl_seconds:
                    continue  # skip expired

                sim = cosine_similarity(query_vec, entry["query_vec"].reshape(1, -1))[0][0]
                if sim > best_score and sim >= self.threshold:
                    best_score = sim
                    best_match = entry

            if best_match:
                logger.debug(f"Semantic cache HIT: {best_score:.3f} for query: {query}")
                if MONITORING_ENABLED:
                    rag_cache_hits_total.labels(cache_type="semantic").inc()
                return best_match["answer"], best_match["sources"]

        if MONITORING_ENABLED:
            rag_cache_misses_total.labels(cache_type="semantic").inc()
        return None

    def set(self, query: str, chat_history: List[Tuple[str, str]], answer: str, sources: List[Document]):
        """Cache the result with embedding."""
        normalized = self._normalize(query)
        search_text = self._build_search_text(normalized, chat_history)
        query_vec = self._embed(search_text)

        with self._lock:
            # LRU eviction
            if len(self.entries) >= self.max_size:
                self.entries.sort(key=lambda x: x["timestamp"])
                self.entries = self.entries[-self.max_size//2:]  # keep newest half + room

            self.entries.append({
                "query": normalized,
                "query_vec": query_vec,
                "answer": answer,
                "sources": sources,
                "timestamp": time.time(),
                "search_text": search_text
            })

    def _build_search_text(self, query: str, chat_history: List[Tuple[str, str]]) -> str:
        """
        Include recent conversation context in the semantic search text.
        This makes follow-up questions match better.
        """
        context = []
        # Take last 2 human messages (most relevant)
        for human, _ in reversed(chat_history[-4:]):
            if human:
                context.append(human.strip())
        context.reverse()
        context.append(query)
        return " | ".join(context[-3:])  # max 3 parts

    def clear(self):
        with self._lock:
            self.entries.clear()

    def stats(self):
        with self._lock:
            now = time.time()
            valid = [e for e in self.entries if now - e["timestamp"] < self.ttl_seconds]
            return {
                "size": len(valid),
                "total": len(self.entries),
                "threshold": self.threshold
            }

# Global semantic cache instance
semantic_cache = SemanticCache(
    threshold=0.93,      # Start with 0.93 → very high confidence match
    max_size=3000,
    ttl_seconds=3600 * 48  # 48 hours
)
```

**Note**: Use numpy-based cosine similarity (already available) instead of sklearn to avoid new dependencies. The existing `EmbeddingCache` class already demonstrates this pattern.

### Step 2: Integrate in aquery() Method

**File**: `backend/rag_pipeline.py`

Replace the cache check block (around line 438-458):

```python
# === 1. Try semantic cache first (broader recall) ===
cached_result = semantic_cache.get(query_text, truncated_history)
if cached_result:
    answer, published_sources = cached_result
    logger.info(f"Semantic cache HIT for: {query_text}")
    metadata = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "duration_seconds": time.time() - start_time,
        "cache_hit": True,
        "cache_type": "semantic",
    }
    return answer, published_sources, metadata

# === 2. Fallback to exact cache (optional — can keep both) ===
cached_result = query_cache.get(query_text, truncated_history)
if cached_result:
    answer, published_sources = cached_result
    logger.debug(f"Cache hit for query: '{query_text}'")
    if MONITORING_ENABLED:
        rag_cache_hits_total.labels(cache_type="query").inc()
        rag_query_duration_seconds.labels(
            query_type="async",
            cache_hit="true"
        ).observe(time.time() - start_time)
    metadata = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "duration_seconds": time.time() - start_time,
        "cache_hit": True,
        "cache_type": "exact",
    }
    return answer, published_sources, metadata
```

After answer generation (around line 602), add:

```python
# Cache in BOTH systems
query_cache.set(query_text, truncated_history, answer, published_sources)  # keep exact
semantic_cache.set(query_text, truncated_history, answer, published_sources)  # semantic
```

### Step 3: Integrate in astream_query() Method

**File**: `backend/rag_pipeline.py`

Similar pattern in `astream_query()` (around line 673-710):

```python
# === 1. Try semantic cache first ===
cached_result = semantic_cache.get(query_text, truncated_history)
if cached_result:
    logger.debug(f"Semantic cache HIT for query: '{query_text}'")
    cached_answer, cached_sources = cached_result
    
    if MONITORING_ENABLED:
        rag_cache_hits_total.labels(cache_type="semantic").inc()
        rag_query_duration_seconds.labels(
            query_type="stream",
            cache_hit="true"
        ).observe(time.time() - start_time)

    # Send sources first
    yield {"type": "sources", "sources": cached_sources}

    # Stream cached response character by character for consistent UX
    for i, char in enumerate(cached_answer):
        yield {"type": "chunk", "content": char}
        if i % 10 == 0:
            await asyncio.sleep(0.001)

    metadata = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "duration_seconds": time.time() - start_time,
        "cache_hit": True,
        "cache_type": "semantic",
    }
    yield {"type": "metadata", "metadata": metadata}
    yield {"type": "complete", "from_cache": True}
    return

# === 2. Fallback to exact cache ===
cached_result = query_cache.get(query_text, truncated_history)
# ... existing exact cache logic ...
```

After answer generation (around line 876), add:

```python
# Cache the result (using truncated history)
query_cache.set(query_text, truncated_history, full_answer_accumulator, published_sources)
semantic_cache.set(query_text, truncated_history, full_answer_accumulator, published_sources)
```

## Configuration

### Environment Variables

Add optional configuration via environment variables:

```bash
# Semantic cache configuration
SEMANTIC_CACHE_THRESHOLD=0.93        # Similarity threshold (0.90-0.95 recommended)
SEMANTIC_CACHE_MAX_SIZE=3000         # Maximum cache entries
SEMANTIC_CACHE_TTL_HOURS=48          # Time-to-live in hours
```

### Threshold Tuning Guide

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| 0.95+ | Very strict (almost exact rephrase) | High accuracy, lower hit rate |
| 0.92–0.94 | **Sweet spot (recommended)** | Balanced accuracy and hit rate |
| 0.90–0.92 | More lenient | Higher hit rate, risk of false positives |
| < 0.90 | Too lenient | Risk of wrong answers |

**Recommendation**: Start with `0.93`, monitor hit rates, and adjust based on:
- `rag_cache_hits_total{cache_type="semantic"}` in Prometheus
- User feedback on answer quality
- Cost savings vs. accuracy trade-off

## Monitoring & Metrics

### Existing Metrics (Already Supported)

The monitoring system already supports `cache_type` labels:

- `rag_cache_hits_total{cache_type="semantic"}` - Semantic cache hits
- `rag_cache_hits_total{cache_type="exact"}` - Exact cache hits
- `rag_cache_misses_total{cache_type="semantic"}` - Semantic cache misses
- `rag_cache_misses_total{cache_type="exact"}` - Exact cache misses

### New Metrics to Consider

Optional enhancements:

- `semantic_cache_size` (Gauge) - Current number of entries
- `semantic_cache_similarity_score` (Histogram) - Distribution of similarity scores
- `semantic_cache_embedding_duration_seconds` (Histogram) - Embedding generation time

### Monitoring Queries

```promql
# Cache hit rate by type
sum(rate(rag_cache_hits_total[5m])) by (cache_type) / 
  (sum(rate(rag_cache_hits_total[5m])) by (cache_type) + 
   sum(rate(rag_cache_misses_total[5m])) by (cache_type))

# Total cache hit rate
sum(rate(rag_cache_hits_total[5m])) / 
  (sum(rate(rag_cache_hits_total[5m])) + sum(rate(rag_cache_misses_total[5m])))
```

## Testing Considerations

### Unit Tests

1. **Similarity Matching**:
   - Test that "What is Litecoin?" matches "Tell me about Litecoin" (similarity > threshold)
   - Test that "What is Bitcoin?" does NOT match "What is Litecoin?" (similarity < threshold)

2. **Chat History Context**:
   - Test that follow-up questions match when history is included
   - Test that same query with different history contexts are handled correctly

3. **LRU Eviction**:
   - Test that oldest entries are evicted when max_size is reached
   - Test that TTL expiration works correctly

4. **Edge Cases**:
   - Empty cache
   - Embedding API failures (graceful degradation)
   - Concurrent access (thread safety)

### Integration Tests

1. **End-to-End Cache Flow**:
   - Query → cache miss → generate answer → cache hit on similar query
   - Verify both semantic and exact caches are populated

2. **Streaming Support**:
   - Verify semantic cache works with `astream_query()`
   - Verify streaming response format matches non-cached responses

3. **Performance**:
   - Measure cache lookup time (< 5ms target)
   - Measure embedding generation time
   - Load test with concurrent requests

## Dependencies

### Required (Already Available)

- `langchain_google_genai` - For `GoogleGenerativeAIEmbeddings` (already in `requirements.txt`)
- `numpy` - For cosine similarity calculation (already in `requirements.txt`)
- `google_api_key` - Environment variable (already required)

### Not Required

- `sklearn` - Use numpy-based cosine similarity instead (avoids new dependency)

## Performance Considerations

### Expected Improvements

- **Cache Hit Rate**: 20-30% → 60-90%
- **Response Latency**: < 5ms for cache hits (vs. 1-3s for LLM generation)
- **Cost Reduction**: 60-90% reduction in LLM API calls for cached queries
- **Memory Usage**: ~2-5MB per 1000 entries (embeddings + metadata)

### Optimization Opportunities

1. **Embedding Caching**: Cache embeddings for identical queries within the same process
2. **Batch Embedding**: Batch multiple queries for embedding generation
3. **Approximate Nearest Neighbor**: Use FAISS or similar for faster similarity search at scale
4. **Redis Backend**: Move to Redis for multi-instance deployments

## Future Enhancements

### Phase 2: Redis-Backed Semantic Cache

For multi-instance deployments, move semantic cache to Redis:

- Shared cache across instances
- Persistence across restarts
- Better scalability

### Phase 3: Hybrid Cache Strategy

Combine multiple caching strategies:

- **Semantic Cache**: For semantic similarity
- **Exact Cache**: For exact matches (fastest)
- **Query Rewriting Cache**: For common rephrasings
- **Context-Aware Cache**: For domain-specific optimizations

### Phase 4: Adaptive Thresholds

Dynamically adjust similarity threshold based on:

- Query complexity
- Domain specificity
- Historical accuracy metrics
- User feedback

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives (wrong answers) | High | Start with conservative threshold (0.93), monitor accuracy |
| Embedding API failures | Medium | Graceful degradation (skip semantic cache, use exact cache) |
| Memory usage | Low | LRU eviction, configurable max_size, TTL expiration |
| Performance overhead | Low | Embedding generation is fast (< 100ms), cache lookup is < 5ms |

## Compatibility with Existing Caches

### Suggested Question Cache

The **Suggested Question Cache** (`SuggestedQuestionCache`) will continue to work independently and will NOT be affected by the semantic cache implementation:

- **Different Purpose**: Suggested Question Cache is for pre-computed answers to UI suggested questions (stored in Payload CMS)
- **Different Location**: Checked in `main.py` endpoint BEFORE the RAG pipeline is called
- **Different Storage**: Redis-based (persistent, shared across instances)
- **Different Matching**: Exact match only, no chat history context
- **Different Flow**: If Suggested Question Cache hits, the request never reaches the RAG pipeline (and thus never checks Semantic Cache)

The semantic cache only affects queries that:
1. Miss the Suggested Question Cache (or have chat history)
2. Enter the RAG pipeline flow
3. Need to be checked against runtime caches

### Query Cache

The existing **Query Cache** (`QueryCache`) will continue to work as a fallback layer:
- Semantic Cache is checked first (broader matching)
- Query Cache is checked second (exact matching)
- Both caches are populated after answer generation
- This provides redundancy and ensures exact matches are still fast

## Success Criteria

1. **Cache Hit Rate**: Achieve 60%+ semantic cache hit rate on production traffic (for queries that reach RAG pipeline)
2. **Accuracy**: Maintain > 95% answer accuracy (no increase in wrong answers)
3. **Performance**: Cache lookup < 5ms, no degradation in response times
4. **Cost Reduction**: 50%+ reduction in LLM API calls for cached queries
5. **Monitoring**: Full visibility into cache performance via Prometheus metrics
6. **Compatibility**: Suggested Question Cache continues to work unchanged

## References

- [LangChain Caching Documentation](https://python.langchain.com/docs/modules/model_io/prompts/prompt_templates/prompt_caching)
- [Semantic Caching Best Practices](https://www.pinecone.io/learn/semantic-caching/)
- Existing implementation: `backend/cache_utils.py` (QueryCache, EmbeddingCache)
- Monitoring: `backend/monitoring/metrics.py` (rag_cache_hits_total, rag_cache_misses_total)

## Implementation Checklist

- [ ] Add `SemanticCache` class to `cache_utils.py`
- [ ] Add global `semantic_cache` instance
- [ ] Integrate semantic cache in `aquery()` method
- [ ] Integrate semantic cache in `astream_query()` method
- [ ] Add cache storage after answer generation
- [ ] Add environment variable configuration
- [ ] Update monitoring/metrics documentation
- [ ] Write unit tests for `SemanticCache` class
- [ ] Write integration tests for cache flow
- [ ] Performance testing and optimization
- [ ] Update deployment documentation
- [ ] Monitor production metrics and tune threshold

