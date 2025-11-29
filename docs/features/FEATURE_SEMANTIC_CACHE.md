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
- Reuses embedding model from `VectorStoreManager` (supports both Google and HuggingFace embeddings)
- Stores query embeddings with cached answers and sources
- Uses cosine similarity with configurable threshold (default: 0.95)
- Includes chat history context in semantic matching
- Implements LRU eviction and TTL-based expiration (default: 72 hours)

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
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import time
import logging
import threading
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class SemanticCache:
    """
    Semantic cache that stores (query → answer + sources) using embedding similarity.
    Reuses the embedding model from VectorStoreManager for consistency with the vector store.
    """
    
    def __init__(self, 
                 embedding_model,  # Embedding model instance from VectorStoreManager
                 threshold: float = 0.95,        # High confidence threshold for semantic matching
                 max_size: int = 2000,
                 ttl_seconds: int = 3600 * 72):  # 72 hours default TTL
        self.embedding_model = embedding_model
        self.threshold = threshold
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # Cache structure: list of dicts (we'll use LRU manually)
        self.entries: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        
        # In-memory cache for embeddings (avoid recomputing for same queries)
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._embedding_cache_max_size = 500

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors using numpy."""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)

    def _embed(self, text: str) -> np.ndarray:
        """Embed a single text with in-memory caching."""
        text_lower = text.strip().lower()
        
        # Check in-memory cache first
        if text_lower in self._embedding_cache:
            return self._embedding_cache[text_lower]
        
        # Generate embedding using the embedding model
        try:
            # Handle both LangChain embeddings and direct model calls
            if hasattr(self.embedding_model, 'embed_query'):
                embedding = self.embedding_model.embed_query(text)
            elif hasattr(self.embedding_model, 'embed_documents'):
                embedding = self.embedding_model.embed_documents([text])[0]
            else:
                # Direct model access (sentence-transformers)
                embedding = self.embedding_model.encode(text, normalize_embeddings=True)
            
            embedding = np.array(embedding, dtype=np.float32)
            
            # Cache in memory (limit size)
            with self._lock:
                if len(self._embedding_cache) >= self._embedding_cache_max_size:
                    # Remove oldest entry (simple FIFO)
                    oldest_key = next(iter(self._embedding_cache))
                    del self._embedding_cache[oldest_key]
                self._embedding_cache[text_lower] = embedding
            
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            raise

    def _normalize(self, query: str) -> str:
        """Normalize query text for consistent matching."""
        return query.strip().lower()

    def get(self, query: str, chat_history: List[Tuple[str, str]] = None) -> Optional[Tuple[str, List[Document]]]:
        """
        Return cached (answer, sources) if semantic similarity > threshold.
        Includes recent chat history in the semantic context.
        """
        normalized = self._normalize(query)
        search_text = self._build_search_text(normalized, chat_history or [])
        
        query_vec = self._embed(search_text)

        with self._lock:
            now = time.time()
            best_match = None
            best_score = 0.0

            # Clean expired entries first
            self.entries = [e for e in self.entries if now - e["timestamp"] < self.ttl_seconds]

            for entry in self.entries:
                entry_vec = entry["query_vec"]
                sim = self._cosine_similarity(query_vec, entry_vec)
                
                if sim > best_score and sim >= self.threshold:
                    best_score = sim
                    best_match = entry

            if best_match:
                logger.debug(f"Semantic cache HIT: similarity={best_score:.3f} for query: {query[:50]}...")
                try:
                    from backend.monitoring.metrics import rag_cache_hits_total
                    rag_cache_hits_total.labels(cache_type="semantic").inc()
                except ImportError:
                    pass  # Monitoring not available
                return best_match["answer"], best_match["sources"]

        try:
            from backend.monitoring.metrics import rag_cache_misses_total
            rag_cache_misses_total.labels(cache_type="semantic").inc()
        except ImportError:
            pass  # Monitoring not available
        return None

    def set(self, query: str, chat_history: List[Tuple[str, str]], answer: str, sources: List[Document]):
        """Cache the result with embedding."""
        normalized = self._normalize(query)
        search_text = self._build_search_text(normalized, chat_history or [])
        query_vec = self._embed(search_text)

        with self._lock:
            # Clean expired entries before adding
            now = time.time()
            self.entries = [e for e in self.entries if now - e["timestamp"] < self.ttl_seconds]
            
            # LRU eviction: remove oldest entries if cache is full
            if len(self.entries) >= self.max_size:
                # Sort by timestamp and keep newest half
                self.entries.sort(key=lambda x: x["timestamp"])
                self.entries = self.entries[-self.max_size//2:]

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
        # Take last 2-3 human messages (most relevant context)
        for human, _ in reversed(chat_history[-4:]):
            if human and isinstance(human, str):
                context.append(human.strip())
        context.reverse()
        context.append(query)
        return " | ".join(context[-3:])  # max 3 parts (recent messages + current query)

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self.entries.clear()
            self._embedding_cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            now = time.time()
            valid = [e for e in self.entries if now - e["timestamp"] < self.ttl_seconds]
            return {
                "size": len(valid),
                "total": len(self.entries),
                "threshold": self.threshold,
                "ttl_seconds": self.ttl_seconds,
                "max_size": self.max_size
            }

# Global semantic cache instance (will be initialized in RAGPipeline)
semantic_cache: Optional[SemanticCache] = None
```

**Important Implementation Notes**:
1. **Embedding Model Reuse**: The SemanticCache reuses the embedding model from `VectorStoreManager.embeddings`, which supports both Google embeddings and HuggingFace sentence-transformers. This ensures consistency with the vector store.
2. **Numpy Cosine Similarity**: Uses numpy-based cosine similarity (same pattern as `EmbeddingCache`) to avoid sklearn dependency: `np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))`.
3. **Initialization**: The semantic cache should be initialized in `RAGPipeline.__init__` after `VectorStoreManager` is created, passing `self.vector_store_manager.embeddings` to the SemanticCache constructor.
4. **Thread Safety**: All cache operations are protected by threading locks to ensure thread-safe access in async contexts.

### Step 1.5: Initialize Semantic Cache in RAGPipeline

**File**: `backend/rag_pipeline.py`

In the `RAGPipeline.__init__` method, after `VectorStoreManager` is initialized (around line 172), add:

```python
from cache_utils import query_cache, semantic_cache

# In RAGPipeline.__init__, after setting up vector_store_manager:
# Initialize semantic cache with the embedding model from VectorStoreManager
from cache_utils import SemanticCache
import os

self.semantic_cache = SemanticCache(
    embedding_model=self.vector_store_manager.embeddings,  # Reuse existing embedding model
    threshold=float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95")),
    max_size=int(os.getenv("SEMANTIC_CACHE_MAX_SIZE", "2000")),
    ttl_seconds=int(os.getenv("SEMANTIC_CACHE_TTL_SECONDS", str(3600 * 72)))  # 72 hours
)
logger.info(f"Semantic cache initialized with threshold={self.semantic_cache.threshold}, TTL={self.semantic_cache.ttl_seconds}s")
```

Also, import the SemanticCache class at the top of the file:

```python
from cache_utils import query_cache, SemanticCache
```

### Step 2: Integrate in aquery() Method

**File**: `backend/rag_pipeline.py`

Replace the cache check block (around line 506-526):

```python
# === 1. Try semantic cache first (broader recall) ===
cached_result = self.semantic_cache.get(query_text, truncated_history)
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

After answer generation (around line 686), add:

```python
# Cache in BOTH systems
query_cache.set(query_text, truncated_history, answer, published_sources)  # keep exact cache
self.semantic_cache.set(query_text, truncated_history, answer, published_sources)  # semantic cache
```

### Step 3: Integrate in astream_query() Method

**File**: `backend/rag_pipeline.py`

Similar pattern in `astream_query()` (around line 673-710):

```python
# === 1. Try semantic cache first ===
cached_result = self.semantic_cache.get(query_text, truncated_history)
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
self.semantic_cache.set(query_text, truncated_history, full_answer_accumulator, published_sources)
```

## Configuration

### Environment Variables

Add optional configuration via environment variables:

```bash
# Semantic cache configuration
SEMANTIC_CACHE_THRESHOLD=0.95        # Similarity threshold (0.95 = very strict, high accuracy)
SEMANTIC_CACHE_MAX_SIZE=2000         # Maximum cache entries
SEMANTIC_CACHE_TTL_SECONDS=259200    # Time-to-live in seconds (72 hours = 3600 * 72)
```

### Threshold Tuning Guide

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| 0.95+ | **Very strict (default)** | Highest accuracy, almost exact semantic match |
| 0.92–0.94 | Balanced | Good accuracy with higher hit rate |
| 0.90–0.92 | More lenient | Higher hit rate, risk of false positives |
| < 0.90 | Too lenient | Risk of wrong answers |

**Recommendation**: The default threshold is set to `0.95` for maximum accuracy. Monitor metrics and adjust based on:
- `rag_cache_hits_total{cache_type="semantic"}` in Prometheus
- User feedback on answer quality
- Cost savings vs. accuracy trade-off

If hit rates are too low (below 30%), consider lowering to 0.93-0.94 after verifying answer quality.

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
| False positives (wrong answers) | High | Start with strict threshold (0.95), monitor accuracy |
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

- [ ] Add `SemanticCache` class to `cache_utils.py` with proper embedding model reuse
- [ ] Initialize semantic cache in `RAGPipeline.__init__` with VectorStoreManager embeddings
- [ ] Integrate semantic cache check in `aquery()` method (before exact cache)
- [ ] Integrate semantic cache check in `astream_query()` method (before exact cache)
- [ ] Add cache storage after answer generation in both methods
- [ ] Add environment variable configuration (SEMANTIC_CACHE_THRESHOLD, SEMANTIC_CACHE_TTL_SECONDS)
- [ ] Test embedding generation with both Google and HuggingFace models
- [ ] Write unit tests for `SemanticCache` class (similarity matching, TTL, LRU eviction)
- [ ] Write integration tests for cache flow (aquery and astream_query)
- [ ] Performance testing (cache lookup < 5ms, embedding generation time)
- [ ] Update deployment documentation with new environment variables
- [ ] Monitor production metrics and tune threshold if needed

