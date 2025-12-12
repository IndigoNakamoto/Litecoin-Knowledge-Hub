# RAG Response Performance Bottlenecks

## Overview

This document identifies the key bottlenecks slowing down RAG responses in the Litecoin Knowledge Hub system.

## Major Bottlenecks

### 1. **Multiple Sequential LLM Calls** ⚠️ HIGHEST IMPACT

The pipeline makes **up to 3 sequential LLM calls** per query:

1. **Query Rewriting** (Line 826 in `rag_pipeline.py`)
   - `await router.rewrite(query_text, truncated_history)`
   - Uses local Ollama or Gemini to rewrite the query
   - **Impact**: ~200-500ms per call

2. **History-Aware Retriever** (Lines 1003/1009)
   - `await self.history_aware_retriever.ainvoke()`
   - Makes **another LLM call** to rewrite the query for retrieval
   - **Problem**: This is redundant when `USE_LOCAL_REWRITER` is enabled and query is already rewritten
   - **Impact**: ~200-500ms per call (duplicate work!)

3. **Final Answer Generation** (Lines 1103/1119)
   - `await self.document_chain.ainvoke()` or `await self.rag_chain.ainvoke()`
   - Generates the final answer from retrieved context
   - **Impact**: ~500-2000ms depending on response length

**Total LLM latency**: ~900-3000ms just for LLM calls

**Recommendation**: 
- Skip history-aware retriever when query is already rewritten by local router
- Consider batching or parallelizing where possible

---

### 2. **Sparse Re-Ranking Document Embedding** ⚠️ HIGH IMPACT

**Location**: Line 969 in `rag_pipeline.py`

```python
_, doc_sparse_list = await infinity.embed_documents(doc_texts)
```

**Problem**: 
- Embeds **ALL candidate documents** (up to `RETRIEVER_K * 2 = 24` docs) for sparse re-ranking
- Each document embedding takes ~50-200ms
- Total: ~1.2-4.8 seconds for 24 documents

**Impact**: This is the **slowest single operation** in the retrieval phase

**Recommendations**:
- Limit sparse re-ranking to top N candidates (e.g., top 10 instead of all 24)
- Cache document sparse embeddings in Redis/MongoDB
- Only perform sparse re-ranking if vector similarity scores are close (narrow margin)
- Consider skipping sparse re-ranking for very high-confidence vector matches

---

### 3. **Sequential Retrieval Operations** ⚠️ MEDIUM IMPACT

**Current Flow** (Lines 900-1012):
1. Query embedding generation (line 852) - ~50-200ms
2. Redis cache lookup (line 864) - ~10-50ms
3. Vector search (line 910) - ~50-200ms
4. BM25 search (line 934) - ~10-100ms
5. Sparse re-ranking (line 969) - ~1.2-4.8s (see above)
6. LLM generation (line 1103) - ~500-2000ms

**Problem**: Operations 3-4 (vector + BM25 search) could run in parallel

**Recommendation**: 
```python
# Parallelize vector and BM25 search
vector_task = asyncio.create_task(vector_search())
bm25_task = asyncio.create_task(bm25_search())
vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
```

**Potential savings**: ~50-200ms

---

### 4. **MongoDB Query Overhead** ⚠️ MEDIUM IMPACT

**Issues**:

1. **Parent Chunks Map Loading** (Line 375-381)
   - Queries up to 20,000 documents on initialization
   - Runs synchronously, blocking pipeline setup
   - **Impact**: ~500ms-2s on startup

2. **Published Docs Loading** (Line 402)
   - `_load_published_docs_from_mongo()` loads all published docs for BM25 indexing
   - Runs on every retriever setup
   - **Impact**: ~100-500ms per setup

**Recommendations**:
- Cache parent chunks map in memory/Redis with TTL
- Lazy-load parent chunks only when FAQ indexing is needed
- Cache published docs list with invalidation on document updates
- Use MongoDB indexes on `metadata.status` and `metadata.chunk_id`

---

### 5. **Redundant History-Aware Retriever** ⚠️ MEDIUM IMPACT

**Location**: Lines 1007-1012

**Problem**: When using Infinity embeddings, the code falls back to `history_aware_retriever` which makes an LLM call, even though:
- The query was already rewritten by the local router (line 826)
- The rewritten query is available and should be used directly

**Current Code**:
```python
except Exception as e:
    logger.warning(f"Infinity hybrid search failed, falling back to history-aware retriever: {e}")
    context_docs = await self.history_aware_retriever.ainvoke({
        "input": retrieval_query,  # Already rewritten!
        "chat_history": converted_chat_history
    })
```

**Recommendation**: 
- When `USE_LOCAL_REWRITER` is enabled and query is rewritten, skip history-aware retriever
- Use rewritten query directly with hybrid retriever (without LLM call)

---

### 6. **Cache Lookup Order** ⚠️ LOW-MEDIUM IMPACT

**Current Order** (Lines 764-896):
1. Semantic cache (in-memory)
2. Exact query cache (in-memory)
3. Query rewriting (LLM call)
4. Query embedding generation
5. Redis vector cache

**Problem**: Query rewriting happens before Redis cache check, meaning:
- Even cached queries trigger an LLM call for rewriting
- Embedding generation happens before checking Redis cache

**Recommendation**:
- Move Redis cache check **before** query rewriting
- Only rewrite if Redis cache misses
- This could save ~200-500ms for cached queries

---

### 7. **Large K Values for Retrieval** ⚠️ LOW-MEDIUM IMPACT

**Current Settings**:
- `RETRIEVER_K = 12` (default)
- Vector search retrieves `RETRIEVER_K * 2 = 24` candidates
- BM25 also retrieves `RETRIEVER_K * 2 = 24` candidates

**Impact**: 
- More documents = more processing time
- More documents = more tokens in LLM context = slower generation

**Recommendation**:
- Reduce initial retrieval to `RETRIEVER_K = 8` for faster responses
- Only increase to 12 if initial results are insufficient
- Consider adaptive K based on query complexity

---

## Performance Optimization Priority

### Immediate Wins (High Impact, Low Effort)

1. **Skip history-aware retriever when query already rewritten**
   - **Savings**: ~200-500ms
   - **Effort**: Low (conditional check)

2. **Limit sparse re-ranking to top 10 candidates**
   - **Savings**: ~600-2400ms
   - **Effort**: Low (change one parameter)

3. **Move Redis cache check before query rewriting**
   - **Savings**: ~200-500ms for cached queries
   - **Effort**: Low (reorder operations)

### Medium-Term Improvements (High Impact, Medium Effort)

4. **Parallelize vector and BM25 search**
   - **Savings**: ~50-200ms
   - **Effort**: Medium (async refactoring)

5. **Cache document sparse embeddings**
   - **Savings**: ~1.2-4.8s per query (after cache warmup)
   - **Effort**: Medium (Redis integration)

6. **Cache parent chunks map**
   - **Savings**: ~500ms-2s on startup, faster FAQ resolution
   - **Effort**: Medium (caching layer)

### Long-Term Optimizations (Medium Impact, High Effort)

7. **Optimize MongoDB queries with indexes**
   - **Savings**: ~100-500ms per query
   - **Effort**: High (database optimization)

8. **Adaptive retrieval K values**
   - **Savings**: Variable (faster for simple queries)
   - **Effort**: High (ML/rule-based system)

---

## Expected Performance Improvements

### Current Performance (Estimated)
- **Cache hit**: ~50-200ms
- **Cache miss (simple query)**: ~2-4 seconds
- **Cache miss (complex query)**: ~4-8 seconds

### After Immediate Wins
- **Cache hit**: ~50-200ms (unchanged)
- **Cache miss (simple query)**: ~1-2 seconds (**50% faster**)
- **Cache miss (complex query)**: ~2-4 seconds (**50% faster**)

### After All Optimizations
- **Cache hit**: ~50-200ms (unchanged)
- **Cache miss (simple query)**: ~0.5-1 second (**75% faster**)
- **Cache miss (complex query)**: ~1-2 seconds (**75% faster**)

---

## Monitoring Recommendations

Add detailed timing metrics for each stage:

```python
# Example metrics to add
rag_query_rewrite_duration_seconds
rag_embedding_generation_duration_seconds
rag_vector_search_duration_seconds
rag_bm25_search_duration_seconds
rag_sparse_rerank_duration_seconds
rag_llm_generation_duration_seconds
```

This will help identify which bottleneck is most impactful in production.

---

## Code Locations

- **Main RAG Pipeline**: `backend/rag_pipeline.py`
  - Query method: `aquery()` (line 654)
  - Stream method: `astream_query()` (line 1259)
- **Vector Store**: `backend/data_ingestion/vector_store_manager.py`
- **Cache Utils**: `backend/cache_utils.py`
- **Monitoring**: `backend/monitoring/metrics.py`

