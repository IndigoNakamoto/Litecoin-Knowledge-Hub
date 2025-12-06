# Feature: High-Performance Local RAG with Cloud Spillover

## Overview

This feature implements a **hybrid RAG pipeline** that prioritizes local resources (Ollama for query rewriting, Infinity for embeddings) but automatically spills over to cloud services (Gemini) when local capacity is exceeded. The goal is to build a scalable system capable of handling **10k DAU** while minimizing cloud API costs and maintaining low latency.

**Status**: 📋 **Planning** - Feature document created

**Priority**: High - Cost optimization and performance enhancement

**Target Hardware**: Mac Mini M4 (24GB RAM)

**Network**: 1 Gbps Fiber

**Last Updated**: 2025-01-XX

---

## Table of Contents

1. [Feature Summary](#feature-summary)
2. [Business Requirements](#business-requirements)
3. [Technical Architecture](#technical-architecture)
4. [Current State Analysis](#current-state-analysis)
5. [Implementation Plan](#implementation-plan)
6. [Integration Points](#integration-points)
7. [Configuration](#configuration)
8. [Risks & Mitigations](#risks--mitigations)
9. [Testing Strategy](#testing-strategy)
10. [Monitoring & Metrics](#monitoring--metrics)
11. [Success Criteria](#success-criteria)
12. [Future Enhancements](#future-enhancements)

---

## Feature Summary

### Problem Statement

The current RAG pipeline relies entirely on cloud services (Gemini) for both query rewriting and LLM generation, which results in:

1. **High API Costs**: Every query requires cloud API calls, even for common/repeated questions
2. **Latency**: Network round-trips add 200-500ms per request
3. **No Local Intelligence**: Underutilizes available local compute (M4 Silicon with 24GB RAM)
4. **Scalability Concerns**: Cloud rate limits and costs scale linearly with traffic
5. **Context Blindness**: Current query rewriting doesn't fully resolve ambiguous follow-up questions

### Solution

Implement a **local-first, cloud-spillover** architecture:

1. **Local Query Rewriting**: Use Ollama (`llama3.2:3b`) to rewrite queries locally, fixing context blindness
2. **Local Embeddings**: Use Infinity (`stella_en_1.5B_v5`) for fast, local embedding generation
3. **Redis Stack Semantic Cache**: Persistent, scalable cache with LFU eviction (4GB limit)
4. **Intelligent Routing**: Route to local services when queue depth < threshold, spill to Gemini when overloaded
5. **Circuit Breaker**: Automatic failover to Gemini on local service timeouts

### Key Benefits

- ✅ **Cost Reduction**: 60-80% reduction in Gemini API calls for common queries
- **Latency Improvement**: 200-500ms faster responses for cached/local queries
- ✅ **Scalability**: Handle 10k DAU with local resources + cloud spillover
- ✅ **Resilience**: Automatic failover prevents service degradation
- ✅ **Context Awareness**: Better query rewriting fixes ambiguous follow-up questions
- ✅ **Resource Efficiency**: Leverages M4 Silicon GPU/Metal acceleration

---

## Business Requirements

### Functional Requirements

1. **FR-1**: System must route queries to local services (Ollama, Infinity) when capacity allows
2. **FR-2**: System must automatically spill over to Gemini when local queue depth exceeds threshold
3. **FR-3**: System must rewrite queries to resolve context blindness (e.g., "Does it expire?" → "Does the $21 plan expire?")
4. **FR-4**: System must cache rewritten queries and responses in Redis Stack with LFU eviction
5. **FR-5**: System must failover to Gemini on local service timeouts (2.0s default)
6. **FR-6**: System must maintain backward compatibility with existing RAG pipeline

### Non-Functional Requirements

1. **NFR-1**: Local query rewriting latency < 500ms (P95)
2. **NFR-2**: Local embedding generation latency < 100ms (P95)
3. **NFR-3**: Cache lookup latency < 10ms (P95)
4. **NFR-4**: System must handle 10k DAU with < 3% error rate
5. **NFR-5**: Local services must use < 4GB RAM each
6. **NFR-6**: Redis Stack must evict entries automatically when memory limit reached

---

## Technical Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Request                            │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Inference Router Service                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Check Queue Depth / Semaphore                           │  │
│  │  IF queue_len < MAX_LOCAL_QUEUE_DEPTH:                   │  │
│  │    → Route to Local Rewriter (Ollama)                    │  │
│  │  ELSE:                                                    │  │
│  │    → Route to Gemini Rewriter (Cloud)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
        ┌──────────────────┐  ┌──────────────────┐
        │ Local Rewriter   │  │ Gemini Rewriter  │
        │ (Ollama)        │  │ (Cloud API)     │
        │ llama3.2:3b     │  │ Gemini 1.5 Flash│
        └────────┬─────────┘  └────────┬─────────┘
                 │                     │
                 └─────────┬──────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │      Rewritten Query                 │
        │  (e.g., "Does the $21 plan expire?")│
        └──────────────┬───────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────┐
        │    Infinity Embedding Service         │
        │    stella_en_1.5B_v5 (Metal)          │
        └──────────────┬───────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────┐
        │    Redis Stack Vector Cache          │
        │    - HNSW Index (1024-dim)            │
        │    - LFU Eviction (4GB limit)         │
        │    - Cosine Similarity (0.90)         │
        └──────────────┬───────────────────────┘
                       │
            ┌───────────┴───────────┐
            │                       │
            ▼                       ▼
    ┌──────────────┐      ┌──────────────┐
    │ Cache HIT    │      │ Cache MISS   │
    │ Return cached │      │ → FAISS      │
    │ response      │      │ → Gemini LLM │
    └───────────────┘      └──────┬───────┘
                                  │
                                  ▼
                        ┌──────────────────┐
                        │ Store in Cache   │
                        └──────────────────┘
```

### Component Overview

| Component | Technology | Purpose | Location |
|-----------|-----------|---------|----------|
| **Inference Router** | Python (FastAPI) | Route queries to local/cloud | `backend/services/router.py` |
| **Query Rewriter** | Ollama (local) / Gemini (cloud) | Fix context blindness | `backend/services/rewriter.py` |
| **Embedding Service** | Infinity (local) | Fast local embeddings | Docker service |
| **Vector Cache** | Redis Stack | Persistent semantic cache | Docker service |
| **Vector Store** | FAISS + MongoDB | Document retrieval | Existing |
| **LLM** | Gemini 2.5 Flash | Answer generation | Existing |

---

## Current State Analysis

### Existing Architecture

**RAG Pipeline Flow** (Current):
```
User Query 
  → Sanitize
  → SemanticCache (in-memory, embedding similarity)
  → QueryCache (in-memory, exact match)
  → History-Aware Retriever (Gemini rewrites query)
  → FAISS Search (local embeddings)
  → Gemini LLM (cloud)
  → Cache result
```

**Infrastructure** (Current):
- ✅ Redis (basic, no vector search)
- ✅ MongoDB (cloud)
- ✅ FAISS (local vector store)
- ❌ No Ollama
- ❌ No Infinity
- ❌ No Redis Stack

**Caching** (Current):
- ✅ `QueryCache` (in-memory, exact match)
- ✅ `SemanticCache` (in-memory, embedding similarity)
- ✅ `SuggestedQuestionCache` (Redis-based)
- ❌ No Redis Stack vector cache

### Integration Challenges

1. **Query Rewriting Duplication**
   - **Current**: `create_history_aware_retriever` uses Gemini for rewriting (line 286-290 in `rag_pipeline.py`)
   - **Proposed**: Separate rewriter service (Ollama/Gemini router)
   - **Solution**: Replace history-aware retriever with pre-rewrite step

2. **Embedding Service Mismatch**
   - **Current**: Direct LangChain embeddings (local or Google)
   - **Proposed**: Infinity HTTP service
   - **Solution**: Create adapter that calls Infinity API

3. **Router/Spillover Missing**
   - **Current**: All queries go directly to Gemini
   - **Proposed**: Queue-based routing with timeout
   - **Solution**: New service layer before RAG pipeline

4. **Redis Stack Vector Cache**
   - **Current**: In-memory `SemanticCache`
   - **Proposed**: Redis Stack with HNSW vector index
   - **Solution**: Migrate `SemanticCache` to Redis Stack

5. **Embedding Dimension Migration**
   - **Current**: `all-mpnet-base-v2` (768-dim) or Google embeddings
   - **Proposed**: `stella_en_1.5B_v5` (1024-dim) - unified architecture
   - **Solution**: Re-index all documents with Infinity embeddings (1024-dim). Create migration script to generate new FAISS index. This provides unified architecture, saves RAM (single model), and improves retrieval quality.

---

## Implementation Plan

### Phase 1: Infrastructure Setup

**Objective**: Add Docker services for local intelligence

**Tasks**:
1. Add Redis Stack service to `docker-compose.prod.yml`
2. Add Ollama service with Metal/GPU support
3. Add Infinity service with Metal acceleration
4. Configure service URLs and networking
5. Test services independently

**Docker Compose Additions**:
```yaml
redis_stack:
  image: redis/redis-stack-server:latest
  container_name: litecoin-redis-stack
  command: >
    sh -c "redis-server
    --maxmemory 4gb
    --maxmemory-policy allkeys-lfu
    --appendonly no"
  ports:
    - "6379:6379"
  volumes:
    - redis_stack_data:/data
  restart: unless-stopped

infinity:
  image: michaelf34/infinity:latest
  container_name: litecoin-infinity
  command: v2 --model-id dunzhang/stella_en_1.5B_v5 --port 7997 --device metal
  ports:
    - "7997:7997"
  volumes:
    - ./model_cache:/app/.cache
  deploy:
    resources:
      limits:
        memory: 4G
  restart: unless-stopped

ollama:
  image: ollama/ollama:latest
  container_name: litecoin-ollama
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  restart: unless-stopped
```

**Initialization Commands**:
```bash
# Pull Ollama model
docker exec -it litecoin-ollama ollama pull llama3.2:3b

# Increase file descriptor limit (Mac)
ulimit -n 65535
```

**Success Criteria**:
- ✅ All services start successfully
- ✅ Ollama responds to health checks
- ✅ Infinity responds to embedding requests
- ✅ Redis Stack accepts connections

**Estimated Time**: 2-4 hours

---

### Phase 2: Configuration & Environment Variables

**Objective**: Define thresholds and service URLs

**New Environment Variables**:
```bash
# Models
LOCAL_REWRITER_MODEL="llama3.2:3b"
EMBEDDING_MODEL_ID="dunzhang/stella_en_1.5B_v5"

# Vector Configuration (Unified 1024-dim architecture)
VECTOR_DIMENSION=1024  # Stella 1.5B embedding dimension

# Router / Spillover Config
MAX_LOCAL_QUEUE_DEPTH=3       # If >3 concurrent requests, use Gemini
LOCAL_TIMEOUT_SECONDS=2.0     # If local hangs, cancel and use Gemini
GEMINI_API_KEY="${GOOGLE_API_KEY}"  # Reuse existing

# Service URLs (Docker internal)
OLLAMA_URL="http://ollama:11434"
INFINITY_URL="http://infinity:7997"
REDIS_STACK_URL="redis://redis_stack:6379"

# Redis Stack Vector Cache Config
REDIS_CACHE_INDEX_NAME="cache:index"
REDIS_CACHE_VECTOR_DIM=1024
REDIS_CACHE_SIMILARITY_THRESHOLD=0.90
```

**Files to Modify**:
- `.env.example` - Add new variables
- `docs/setup/ENVIRONMENT_VARIABLES.md` - Document new variables

**Success Criteria**:
- ✅ All environment variables documented
- ✅ Default values are sensible
- ✅ Configuration is validated on startup

**Estimated Time**: 1 hour

---

### Phase 3: Application Logic - Router Service

**Objective**: Create intelligent routing service

**New File**: `backend/services/router.py`

**Key Components**:
1. **Queue Depth Tracking**: Use Redis or in-memory semaphore
2. **Routing Logic**: Route based on queue depth
3. **Circuit Breaker**: Timeout handling with Gemini fallback
4. **Metrics**: Track routing decisions

**Implementation**:
```python
class InferenceRouter:
    def __init__(self):
        self.max_queue_depth = int(os.getenv("MAX_LOCAL_QUEUE_DEPTH", "3"))
        self.local_timeout = float(os.getenv("LOCAL_TIMEOUT_SECONDS", "2.0"))
        self.local_rewriter = LocalRewriter()
        self.gemini_rewriter = GeminiRewriter()
        self._queue_semaphore = asyncio.Semaphore(self.max_queue_depth)
    
    async def rewrite(self, query: str, chat_history: List[Tuple[str, str]]) -> str:
        """Route to local or cloud rewriter based on queue depth."""
        # Check queue depth
        if self._queue_semaphore.locked():
            logger.info("Local queue full, spilling to Gemini")
            return await self.gemini_rewriter.rewrite(query, chat_history)
        
        # Try local with timeout
        try:
            async with asyncio.timeout(self.local_timeout):
                async with self._queue_semaphore:
                    return await self.local_rewriter.rewrite(query, chat_history)
        except asyncio.TimeoutError:
            logger.warning("Local rewriter timeout, failing over to Gemini")
            return await self.gemini_rewriter.rewrite(query, chat_history)
```

**Success Criteria**:
- ✅ Router correctly routes based on queue depth
- ✅ Timeout handling works correctly
- ✅ Metrics track routing decisions
- ✅ Circuit breaker prevents cascading failures

**Estimated Time**: 4-6 hours

---

### Phase 4: Query Rewriter Service

**Objective**: Implement query rewriting with context awareness

**New File**: `backend/services/rewriter.py`

**Key Components**:
1. **Local Rewriter**: Ollama-based rewriting
2. **Gemini Rewriter**: Cloud-based rewriting (fallback)
3. **System Prompt**: Context-aware query resolution
4. **NO_SEARCH_NEEDED**: Handle non-search queries

**System Prompt**:
```
You are a Query Resolution Engine. Rewrite the User's input into a standalone, 
context-complete search query based on the Chat History. Remove filler words. 
If no search is needed (e.g. 'thanks'), output: NO_SEARCH_NEEDED. 
DO NOT answer the question.
```

**Implementation**:
```python
class LocalRewriter:
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = os.getenv("LOCAL_REWRITER_MODEL", "llama3.2:3b")
    
    async def rewrite(self, query: str, chat_history: List[Tuple[str, str]]) -> str:
        """Rewrite query using Ollama."""
        # Build prompt with chat history
        prompt = self._build_prompt(query, chat_history)
        
        # Call Ollama API
        response = await self._call_ollama(prompt)
        
        # Parse response
        if response.strip() == "NO_SEARCH_NEEDED":
            return "NO_SEARCH_NEEDED"
        
        return response.strip()

class GeminiRewriter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        # Use existing Gemini client setup
    
    async def rewrite(self, query: str, chat_history: List[Tuple[str, str]]) -> str:
        """Rewrite query using Gemini (fallback)."""
        # Similar implementation using Gemini API
```

**Success Criteria**:
- ✅ Rewriter fixes context blindness (e.g., "Does it expire?" → "Does the $21 plan expire?")
- ✅ Handles NO_SEARCH_NEEDED correctly
- ✅ Works with both local and cloud backends
- ✅ Latency < 500ms for local, < 1000ms for cloud

**Estimated Time**: 6-8 hours

---

### Phase 5: Infinity Embedding Adapter (Unified Architecture)

**Objective**: Integrate Infinity service for local embeddings

**New File**: `backend/services/infinity_adapter.py`

**Key Components**:
1. **HTTP Client**: Call Infinity API
2. **Adapter Interface**: Compatible with LangChain embeddings
3. **Error Handling**: Fallback to existing embeddings

**Implementation**:
```python
class InfinityEmbeddings:
    def __init__(self):
        self.infinity_url = os.getenv("INFINITY_URL", "http://localhost:7997")
        self.model_id = os.getenv("EMBEDDING_MODEL_ID", "dunzhang/stella_en_1.5B_v5")
    
    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.infinity_url}/embeddings",
                json={"model": self.model_id, "input": text}
            )
            return response.json()["data"][0]["embedding"]
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents."""
        # Batch processing
```

**Integration Point**: Infinity will be used as the primary embedding service (replacing existing embeddings)

**Success Criteria**:
- ✅ Infinity adapter works with existing code
- ✅ Embedding quality is acceptable (1024-dim vectors)
- ✅ Latency < 100ms per query
- ✅ Batch processing supports efficient embedding generation

**Estimated Time**: 4-6 hours

---

### Phase 5.5: Vector Re-indexing Script

**Objective**: Create migration script to re-index all documents with 1024-dim Infinity embeddings

**New File**: `scripts/reindex_vectors.py`

**Key Components**:
1. **Infinity Client**: Initialize InfinityEmbeddings wrapper
2. **Document Fetching**: Load all chunks from MongoDB
3. **Batch Embedding**: Process in batches (batch size 32 for M4)
4. **FAISS Index Creation**: Initialize new 1024-dim FAISS index
5. **Index Saving**: Save new index to disk

**Implementation**:
```python
import faiss
import numpy as np
from backend.services.infinity_adapter import InfinityEmbeddings
from backend.data_ingestion.vector_store_manager import VectorStoreManager

async def reindex_vectors():
    """Re-index all vectors using Infinity 1024-dim embeddings."""
    # Initialize Infinity embeddings
    infinity_embeddings = InfinityEmbeddings()
    
    # Fetch all documents from MongoDB
    vector_store_manager = VectorStoreManager()
    all_docs = list(vector_store_manager.collection.find({}))
    
    print(f"Found {len(all_docs)} documents to re-index")
    
    # Batch embed documents (batch size 32 for M4)
    BATCH_SIZE = 32
    all_vectors = []
    texts = [doc["text"] for doc in all_docs]
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        batch_vectors = await infinity_embeddings.embed_documents(batch)
        all_vectors.extend(batch_vectors)
        print(f"Processed {min(i + BATCH_SIZE, len(texts))}/{len(texts)} documents")
    
    # Convert to numpy array
    vectors = np.array(all_vectors, dtype=np.float32)
    
    # Initialize new FAISS index (1024 dimensions)
    index = faiss.IndexFlatL2(1024)
    
    # Normalize vectors for cosine similarity
    faiss.normalize_L2(vectors)
    
    # Add vectors to index
    index.add(vectors)
    
    # Save new index
    faiss.write_index(index, "backend/faiss_index/index_1024.faiss")
    
    # Save metadata mapping
    # ... save document IDs and metadata mapping
    
    print(f"✅ Re-indexing complete: {len(all_vectors)} vectors, dimension 1024")
```

**Usage**:
```bash
python scripts/reindex_vectors.py
```

**Success Criteria**:
- ✅ All documents re-indexed with 1024-dim vectors
- ✅ New FAISS index saved to disk
- ✅ Metadata mapping preserved
- ✅ Index is compatible with Infinity embeddings

**Estimated Time**: 2-4 hours (depends on document count)

---

### Phase 6: Redis Stack Vector Cache

**Objective**: Migrate semantic cache to Redis Stack

**New File**: `backend/services/redis_vector_cache.py`

**Key Components**:
1. **Index Creation**: HNSW vector index on startup
2. **Vector Search**: KNN search with similarity threshold
3. **LFU Eviction**: Automatic eviction when memory limit reached
4. **Cache Storage**: Store rewritten query vectors + responses

**Index Schema**:
```python
# Redis Stack Index Definition
INDEX_NAME = "cache:index"
SCHEMA = {
    "embedding": {
        "type": "VECTOR",
        "ALGORITHM": "HNSW",
        "TYPE": "FLOAT32",
        "DIM": 1024,
        "DISTANCE_METRIC": "COSINE"
    },
    "response": {"type": "TEXT"},
    "query": {"type": "TEXT"}
}
```

**Implementation**:
```python
class RedisVectorCache:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_STACK_URL", "redis://localhost:6379")
        self.threshold = float(os.getenv("REDIS_CACHE_SIMILARITY_THRESHOLD", "0.90"))
        self._ensure_index()
    
    async def get(self, query_vector: List[float]) -> Optional[Tuple[str, List[Document]]]:
        """Search cache using vector similarity."""
        # KNN search with threshold
        results = await self.redis_client.ft(INDEX_NAME).search(
            f"*=>[KNN 1 @embedding $vec AS score]",
            query_params={"vec": np.array(query_vector).tobytes()}
        )
        
        if results and results[0].score >= self.threshold:
            return results[0].response, results[0].sources
        
        return None
    
    async def set(self, query_vector: List[float], response: str, sources: List[Document]):
        """Store in cache with vector."""
        key = f"cache:{hashlib.md5(query_vector.tobytes()).hexdigest()}"
        await self.redis_client.hset(key, mapping={
            "embedding": np.array(query_vector).tobytes(),
            "response": response,
            "sources": json.dumps(sources)
        })
```

**Migration Strategy**:
1. Create Redis Stack index on startup
2. Gradually migrate entries from in-memory cache
3. Keep in-memory cache as fallback during transition
4. Monitor hit rates and performance

**Success Criteria**:
- ✅ Redis Stack index created successfully
- ✅ Vector search works correctly
- ✅ LFU eviction functions properly
- ✅ Cache hit rates match or exceed in-memory cache
- ✅ Latency < 10ms for cache lookups

**Estimated Time**: 8-10 hours

---

### Phase 7: RAG Pipeline Integration

**Objective**: Integrate new services into existing RAG pipeline

**File to Modify**: `backend/rag_pipeline.py`

**Key Changes**:
1. **Replace History-Aware Retriever**: Use router-based rewriting instead
2. **Unified Infinity Embeddings**: Use Infinity (1024-dim) for both cache and FAISS search
3. **Load Re-indexed FAISS**: Load the new 1024-dim FAISS index
4. **Add Redis Cache Check**: Check Redis Stack cache before FAISS search
5. **Simplified Architecture**: One embedding call for everything

**Modified Flow**:
```python
async def aquery(self, query_text: str, chat_history: List[Tuple[str, str]]):
    # 1. Router-based rewriting
    router = InferenceRouter()
    rewritten_query = await router.rewrite(query_text, chat_history)
    
    if rewritten_query == "NO_SEARCH_NEEDED":
        return "I understand. How else can I help?", [], metadata
    
    # 2. Embed rewritten query (Infinity - 1024 dim)
    infinity_embeddings = InfinityEmbeddings()
    query_vector = await infinity_embeddings.embed_query(rewritten_query)
    
    # 3. Check Redis Stack cache
    redis_cache = RedisVectorCache()
    cached_result = await redis_cache.get(query_vector)
    if cached_result:
        return cached_result
    
    # 4. FAISS search (using same 1024-dim vector - compatible after re-indexing!)
    # We can pass the EXACT SAME vector to FAISS because we re-indexed!
    context_docs = await self.vector_store_manager.vector_store.similarity_search_by_vector(
        query_vector, k=RETRIEVER_K
    )
    
    # 5. Generate answer (Gemini)
    answer = await self.llm.ainvoke(...)
    
    # 6. Store in Redis cache
    await redis_cache.set(query_vector, answer, sources)
```

**Feature Flags**:
```python
USE_LOCAL_REWRITER = os.getenv("USE_LOCAL_REWRITER", "false").lower() == "true"
USE_INFINITY_EMBEDDINGS = os.getenv("USE_INFINITY_EMBEDDINGS", "false").lower() == "true"
USE_REDIS_CACHE = os.getenv("USE_REDIS_CACHE", "false").lower() == "true"
```

**Success Criteria**:
- ✅ Integration works with feature flags
- ✅ Backward compatibility maintained
- ✅ Performance meets targets
- ✅ Error handling is robust

**Estimated Time**: 10-12 hours

---

## Integration Points

### Current System Integration

| Component | Current | New Integration | Impact |
|-----------|---------|-----------------|--------|
| **Query Rewriting** | Gemini (in retriever) | Router → Ollama/Gemini | Replace history-aware retriever |
| **Embeddings** | LangChain local/Google (768-dim) | Infinity (1024-dim) | Replace entirely, re-index required |
| **Vector Cache** | In-memory SemanticCache | Redis Stack | Migrate gradually |
| **Vector Store** | FAISS (768-dim) | FAISS (1024-dim after re-index) | Re-index all documents |
| **LLM** | Gemini | Gemini (unchanged) | No changes |

### Compatibility Matrix

| Component | Current | Proposed | Compatible? | Migration Strategy |
|-----------|---------|----------|------------|-------------------|
| Embeddings | LangChain local/Google (768-dim) | Infinity HTTP (1024-dim) | Needs re-indexing | Run re-indexing script |
| Query Rewriting | Gemini (in retriever) | Ollama/Gemini router | Needs refactor | Feature flag |
| Vector Cache | In-memory | Redis Stack | Needs migration | Gradual migration |
| Vector Store | FAISS (768-dim) | FAISS (1024-dim) | Needs re-indexing | Run re-indexing script |
| LLM | Gemini | Gemini (unchanged) | ✅ Yes | No changes |

---

## Configuration

### Environment Variables

**New Variables** (add to `.env.example`):
```bash
# Local Models
LOCAL_REWRITER_MODEL="llama3.2:3b"
EMBEDDING_MODEL_ID="dunzhang/stella_en_1.5B_v5"

# Vector Configuration (Unified 1024-dim architecture)
VECTOR_DIMENSION=1024  # Stella 1.5B embedding dimension

# Router / Spillover Config
MAX_LOCAL_QUEUE_DEPTH=3
LOCAL_TIMEOUT_SECONDS=2.0
GEMINI_API_KEY="${GOOGLE_API_KEY}"

# Service URLs (Docker internal)
OLLAMA_URL="http://ollama:11434"
INFINITY_URL="http://infinity:7997"
REDIS_STACK_URL="redis://redis_stack:6379"

# Redis Stack Vector Cache
REDIS_CACHE_INDEX_NAME="cache:index"
REDIS_CACHE_VECTOR_DIM=1024
REDIS_CACHE_SIMILARITY_THRESHOLD=0.90

# Feature Flags (gradual rollout)
USE_LOCAL_REWRITER=false
USE_INFINITY_EMBEDDINGS=false
USE_REDIS_CACHE=false
```

### Configuration Tuning Guide

| Parameter | Default | Tuning Guide |
|-----------|---------|--------------|
| `MAX_LOCAL_QUEUE_DEPTH` | 3 | Increase for higher throughput, decrease for lower latency |
| `LOCAL_TIMEOUT_SECONDS` | 2.0 | Increase if Ollama is slow, decrease for faster failover |
| `REDIS_CACHE_SIMILARITY_THRESHOLD` | 0.90 | Lower = more hits but risk of false positives |
| `REDIS_CACHE_VECTOR_DIM` | 1024 | Must match Infinity embedding dimension |

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Re-indexing Time** | Medium | Medium | Run re-indexing script during low-traffic period, test thoroughly |
| **Query Rewriting Quality** | Medium | Low | Test with real queries, fallback to Gemini if quality degrades |
| **Local Service Reliability** | Medium | Medium | Circuit breaker with automatic Gemini failover |
| **Redis Stack Memory Limits** | Low | Low | LFU eviction handles memory pressure automatically |
| **Migration Complexity** | Medium | Medium | Re-indexing script automates migration, feature flags allow gradual rollout |
| **Performance Degradation** | Medium | Low | Monitor metrics, rollback via feature flags |
| **Ollama Model Quality** | Medium | Low | Test extensively, compare with Gemini rewriting |

### Critical Decisions

1. **Embedding Dimensions**: 
   - **Option A**: Use Infinity (1024-dim) for cache only, keep existing (768-dim) for FAISS
   - **Option B**: Rebuild FAISS index with Infinity embeddings (1024-dim) - **SELECTED**
   - **Rationale**: Dataset is small enough to re-index. This removes the need for legacy embedding support, saves RAM (only 1 model loaded), and improves retrieval quality by using Stella 1.5B for document search too.

2. **Query Rewriting Strategy**:
   - **Option A**: Replace history-aware retriever entirely
   - **Option B**: Keep both, use router for pre-rewrite
   - **Recommendation**: Option A (cleaner, avoids duplication)

3. **Cache Migration**:
   - **Option A**: Big bang migration (all at once)
   - **Option B**: Gradual migration (dual-write, then cutover)
   - **Recommendation**: Option B (safer, allows rollback)

---

## Testing Strategy

### Unit Tests

1. **Router Service**:
   - Test queue depth routing logic
   - Test timeout handling
   - Test circuit breaker behavior

2. **Query Rewriter**:
   - Test context blindness fixes
   - Test NO_SEARCH_NEEDED handling
   - Test both local and cloud backends

3. **Infinity Adapter**:
   - Test embedding generation
   - Test error handling
   - Test fallback behavior

4. **Redis Vector Cache**:
   - Test index creation
   - Test vector search
   - Test LFU eviction

### Integration Tests

1. **End-to-End Flow**:
   - Test complete flow: query → rewrite → embed → cache → search → generate
   - Test cache hit path
   - Test cache miss path
   - Test spillover to Gemini

2. **Performance Tests**:
   - Test latency targets (< 500ms rewriting, < 100ms embedding, < 10ms cache)
   - Test throughput (10k DAU simulation)
   - Test memory usage (< 4GB per service)

3. **Failure Scenarios**:
   - Test Ollama timeout → Gemini failover
   - Test Infinity failure → fallback
   - Test Redis Stack unavailability → in-memory fallback

### Load Tests

1. **Concurrent Requests**: Simulate 10k DAU
2. **Queue Depth**: Test spillover triggers correctly
3. **Memory Pressure**: Test LFU eviction under load
4. **Cost Tracking**: Measure Gemini API call reduction

---

## Monitoring & Metrics

### New Metrics

```python
# Router metrics
local_rewriter_requests_total = Counter("local_rewriter_requests_total")
gemini_rewriter_requests_total = Counter("gemini_rewriter_requests_total")
router_spillover_total = Counter("router_spillover_total")
local_rewriter_timeout_total = Counter("local_rewriter_timeout_total")

# Rewriter latency
rewriter_latency_seconds = Histogram("rewriter_latency_seconds", ["backend"])

# Infinity embeddings
infinity_embedding_requests_total = Counter("infinity_embedding_requests_total")
infinity_embedding_latency_seconds = Histogram("infinity_embedding_latency_seconds")

# Redis Stack cache
redis_cache_hits_total = Counter("redis_cache_hits_total")
redis_cache_misses_total = Counter("redis_cache_misses_total")
redis_cache_size = Gauge("redis_cache_size")
redis_cache_memory_usage_bytes = Gauge("redis_cache_memory_usage_bytes")
```

### Key Performance Indicators

1. **Cost Reduction**: 60-80% reduction in Gemini API calls
2. **Latency Improvement**: 200-500ms faster for cached queries
3. **Cache Hit Rate**: 60-90% for rewritten queries
4. **Spillover Rate**: < 10% of requests spill to Gemini
5. **Error Rate**: < 3% under 10k DAU load

### Grafana Dashboards

1. **Router Dashboard**: Routing decisions, spillover rate, timeout rate
2. **Rewriter Dashboard**: Latency by backend, quality metrics
3. **Cache Dashboard**: Hit rate, memory usage, eviction rate
4. **Cost Dashboard**: Gemini API calls, cost savings

---

## Success Criteria

### Functional Success

- ✅ Router correctly routes to local/cloud based on queue depth
- ✅ Query rewriting fixes context blindness (90%+ accuracy)
- ✅ Redis Stack cache achieves 60%+ hit rate
- ✅ System handles 10k DAU with < 3% error rate
- ✅ Automatic failover works correctly

### Performance Success

- ✅ Local rewriting latency < 500ms (P95)
- ✅ Local embedding latency < 100ms (P95)
- ✅ Cache lookup latency < 10ms (P95)
- ✅ 60-80% reduction in Gemini API calls
- ✅ 200-500ms latency improvement for cached queries

### Business Success

- ✅ Cost savings: 60-80% reduction in cloud API costs
- ✅ Scalability: System handles 10k DAU
- ✅ User experience: Faster responses for common queries
- ✅ Reliability: < 3% error rate under load

---

## Response Quality Optimization

### Current Configuration

The current RAG pipeline uses:
- **Model**: `gemini-2.5-flash-lite-preview-09-2025` (lite version)
- **Documents Retrieved**: `RETRIEVER_K = 8` (configurable via env var)
- **Temperature**: `0.2` (conservative, very factual)
- **Max Output Tokens**: Not explicitly set (defaults to model maximum)
- **Chat History**: `MAX_CHAT_HISTORY_PAIRS = 2` (last 2 exchanges)

### Options to Improve Response Quality

#### 1. Increase Documents Retrieved (Easiest, Low Cost)

**Impact**: Medium  
**Cost**: Low (more context tokens, same generation cost)

```python
# Current: RETRIEVER_K = 8
# Recommended: RETRIEVER_K = 12 or 16
```

**Pros**:
- More context for the model
- Better coverage of related topics
- Easy to test and tune

**Cons**:
- More input tokens (higher cost)
- Risk of irrelevant docs diluting context
- Slightly slower retrieval

**Recommendation**: Start with `RETRIEVER_K=12`, monitor quality vs. cost.

---

#### 2. Increase Max Output Tokens (If Responses Are Being Cut Off)

**Impact**: High (if truncation is the issue)  
**Cost**: Medium (more output tokens)

```python
# Add to ChatGoogleGenerativeAI initialization:
self.llm = ChatGoogleGenerativeAI(
    model=LLM_MODEL_NAME,
    temperature=0.2,
    max_output_tokens=4096,  # or 8192 if model supports it
    google_api_key=google_api_key,
    ...
)
```

**Pros**:
- Allows longer, more detailed responses
- Better for complex topics requiring depth

**Cons**:
- Higher cost per response
- Slower generation
- May produce unnecessarily verbose answers

**Recommendation**: Only if responses are being truncated. Check if answers end mid-sentence.

---

#### 3. Upgrade to Larger Model (Highest Impact, Higher Cost)

**Impact**: High  
**Cost**: High

**Current**: `gemini-2.5-flash-lite-preview-09-2025`  
**Options**:
- `gemini-2.5-flash-preview-09-2025` (full Flash, better quality)
- `gemini-2.0-flash-exp` (if available)
- `gemini-1.5-pro` (best quality, slower/more expensive)

**Pros**:
- Better understanding and reasoning
- More nuanced responses
- Better at following complex instructions

**Cons**:
- Higher cost (2-5x)
- Slower latency
- May be overkill for simple queries

**Recommendation**: Test `gemini-2.5-flash-preview` first (drop the "lite"). Good balance of quality and cost.

---

#### 4. Adjust Temperature (Free, Quick Test)

**Impact**: Low-Medium  
**Cost**: None

```python
# Current: temperature=0.2 (very conservative)
# Recommended: temperature=0.4-0.6 (more natural, slightly more creative)
```

**Pros**:
- More natural language
- Better for conversational tone
- No cost change

**Cons**:
- Slightly less deterministic
- May occasionally hallucinate

**Recommendation**: Try `0.4` for more natural tone while staying factual.

---

### Recommended Testing Order

1. **Increase `RETRIEVER_K` to 12**
   - Set `RETRIEVER_K=12` in env
   - Test on a few queries
   - Monitor cost vs. quality

2. **Upgrade Model** (if budget allows)
   - Change to `gemini-2.5-flash-preview-09-2025`
   - Compare quality on same queries

3. **Increase Max Output Tokens** (if truncation occurs)
   - Add `max_output_tokens=4096` to LLM init
   - Monitor if responses improve

4. **Adjust Temperature** (optional)
   - Try `0.4` for more natural responses

### Cost Impact Estimate

| Change | Cost Multiplier | Latency Impact |
|--------|----------------|----------------|
| `RETRIEVER_K: 8→12` | ~1.2x (input tokens) | +50-100ms |
| `max_output_tokens: default→4096` | ~1.5-2x (output tokens) | +200-500ms |
| `lite → flash` | ~2-3x | +100-300ms |
| `flash → pro` | ~5-10x | +500-1000ms |

### Quick Win Configuration

For immediate quality improvement with moderate cost increase:

```python
# In backend/rag_pipeline.py:
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "12"))  # Changed from 8
LLM_MODEL_NAME = "gemini-2.5-flash-preview-09-2025"  # Drop "lite"
temperature=0.4,  # Changed from 0.2
```

**Expected Results**:
- More context (12 docs vs 8)
- Better model quality (flash vs lite)
- More natural tone (temp 0.4 vs 0.2)
- Moderate cost increase (~2-3x)

---


### Phase 2: Advanced Optimizations

1. **Adaptive Queue Depth**: Dynamically adjust `MAX_LOCAL_QUEUE_DEPTH` based on load
2. **Query Deduplication**: Detect and cache duplicate queries across users
3. **Batch Processing**: Batch multiple queries for Ollama/Infinity
4. **Model Fine-tuning**: Fine-tune Ollama model on domain-specific queries

### Phase 3: Multi-Model Support

1. **Model Selection**: Choose best model per query type
2. **A/B Testing**: Compare local vs. cloud rewriting quality
3. **Quality Metrics**: Track rewriting accuracy and user satisfaction

### Phase 4: Distributed Architecture

1. **Multi-Instance**: Share Redis Stack cache across instances
2. **Load Balancing**: Distribute load across multiple Ollama instances
3. **Regional Deployment**: Deploy local services in multiple regions

---

## Implementation Checklist

### Phase 1: Infrastructure
- [ ] Add Redis Stack to docker-compose
- [ ] Add Ollama service with Metal support
- [ ] Add Infinity service with Metal acceleration
- [ ] Test all services independently
- [ ] Document service URLs and configuration

### Phase 2: Configuration
- [ ] Add environment variables to `.env.example`
- [ ] Document configuration in `ENVIRONMENT_VARIABLES.md`
- [ ] Add validation for new variables
- [ ] Set sensible defaults

### Phase 3: Router Service
- [ ] Create `backend/services/router.py`
- [ ] Implement queue depth tracking
- [ ] Implement routing logic
- [ ] Add circuit breaker
- [ ] Add metrics
- [ ] Write unit tests

### Phase 4: Query Rewriter
- [ ] Create `backend/services/rewriter.py`
- [ ] Implement LocalRewriter (Ollama)
- [ ] Implement GeminiRewriter (fallback)
- [ ] Add system prompt
- [ ] Handle NO_SEARCH_NEEDED
- [ ] Write unit tests

### Phase 5: Infinity Adapter (Unified Architecture)
- [ ] Create `backend/services/infinity_adapter.py`
- [ ] Implement HTTP client for 1024-dim embeddings
- [ ] Create LangChain-compatible interface
- [ ] Add batch processing support (batch size 32)
- [ ] Write unit tests

### Phase 5.5: Vector Re-indexing
- [ ] Create `scripts/reindex_vectors.py`
- [ ] Implement document fetching from MongoDB
- [ ] Implement batch embedding with Infinity
- [ ] Create new 1024-dim FAISS index
- [ ] Save index and metadata mapping
- [ ] Test re-indexing on sample data

### Phase 6: Redis Stack Cache
- [ ] Create `backend/services/redis_vector_cache.py`
- [ ] Implement index creation
- [ ] Implement vector search
- [ ] Implement cache storage
- [ ] Test LFU eviction
- [ ] Write unit tests

### Phase 7: RAG Pipeline Integration
- [ ] Modify `rag_pipeline.py` to use router
- [ ] Replace history-aware retriever
- [ ] Add Infinity embeddings option
- [ ] Add Redis Stack cache check
- [ ] Add feature flags
- [ ] Write integration tests

### Phase 8: Re-indexing & Migration
- [ ] Run re-indexing script on production data
- [ ] Verify new FAISS index integrity
- [ ] Test search quality with new embeddings
- [ ] Update VectorStoreManager to load new index
- [ ] Document migration procedure

### Phase 9: Testing & Validation
- [ ] Write unit tests for all services
- [ ] Write integration tests
- [ ] Perform load testing (10k DAU)
- [ ] Validate performance targets
- [ ] Test failure scenarios

### Phase 10: Documentation & Deployment
- [ ] Update architecture documentation
- [ ] Create deployment guide
- [ ] Add monitoring dashboards
- [ ] Document rollback procedure
- [ ] Create runbook for operations

---

## References

- [Ollama Documentation](https://ollama.ai/docs)
- [Infinity Embeddings](https://github.com/michaelf34/infinity)
- [Redis Stack Vector Search](https://redis.io/docs/stack/search/)
- [LangChain Embeddings](https://python.langchain.com/docs/integrations/text_embedding/)
- Existing implementation: `backend/rag_pipeline.py`, `backend/cache_utils.py`

---

## Appendix: Decision Log

### Decision 1: Embedding Dimension Strategy
**Date**: 2025-01-XX  
**Status**: 🔄 **CHANGED**  
**Old Decision**: Option A (Hybrid/Compatibility Mode) - Use Infinity (1024-dim) for cache only, keep existing (768-dim) for FAISS  
**New Decision**: Option B (Unified 1024-dim Architecture) - Rebuild FAISS index with Infinity embeddings (1024-dim)  
**Rationale**: Dataset is small enough to re-index. This removes the need for legacy embedding support, saves RAM (only 1 model loaded), and improves retrieval quality by using Stella 1.5B for document search too.  
**Status**: ✅ Approved

### Decision 2: Query Rewriting Strategy  
**Date**: 2025-01-XX  
**Decision**: Replace history-aware retriever with router-based rewriting  
**Rationale**: Cleaner architecture, avoids duplication  
**Status**: ✅ Approved

### Decision 3: Cache Migration Strategy  
**Date**: 2025-01-XX  
**Decision**: Gradual migration with dual-write, then cutover  
**Rationale**: Safer, allows rollback  
**Status**: ✅ Approved

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-XX  
**Author**: System Architecture Team  
**Reviewers**: TBD

