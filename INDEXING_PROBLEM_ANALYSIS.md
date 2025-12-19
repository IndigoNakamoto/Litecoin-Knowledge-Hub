# Indexing Problem Analysis

## Summary

The indexing system is **correctly configured** and the **semantic retrieval problem has been RESOLVED** via query expansion for rare entities.

## ✅ RESOLVED (2024-12-19)

### The Fix: Query Expansion for Rare Entities

**Problem**: Queries like "explain litvm" failed to retrieve LitVM documents because:
- LitVM document was at rank 422 (outside top 24 retrieval window)
- Semantic similarity was only 0.291 (below 0.3 threshold)
- BM25 prioritized "explain" over "litvm"

**Solution**: Added automatic query expansion in `backend/utils/litecoin_vocabulary.py`:

```python
LTC_ENTITY_EXPANSIONS = {
    "litvm": "litecoin virtual machine zero-knowledge omnichain smart contracts",
    "mweb": "mimblewimble extension blocks privacy confidential transactions",
    # ... more entities
}
```

**Result**:
| Metric | Before | After |
|--------|--------|-------|
| LitVM Rank | 422 | Top 12 ✅ |
| Similarity Score | 0.291 | 0.448 ✅ |
| Vector Candidates | Not retrieved | 24 above threshold ✅ |
| Documents Retrieved | 0 | 8 unique ✅ |

---

## ✅ What's Working Correctly

### 1. Index Type (FIXED)
- **Status**: ✅ Fixed
- **Issue**: Previously using `IndexFlatL2` (L2 distance) instead of `IndexFlatIP` (inner product for cosine similarity)
- **Fix**: Reindexed with `IndexFlatIP` after L2 normalization
- **Verification**: 
  - Index type: `IndexFlatIP` ✅
  - Metric: 0 (InnerProduct) ✅
  - Dimension: 1024 ✅
  - Vectors: 2,107 ✅

### 2. Embedding Configuration
- **Status**: ✅ Correct
- **Embedding Service**: Infinity (`BAAI/bge-m3`)
- **Dimension Match**: Query embeddings (1024) = Index dimension (1024) ✅
- **Index Path**: `/app/backend/faiss_index_1024` ✅
- **Environment**: `USE_INFINITY_EMBEDDINGS=true` ✅

### 3. Document Embedding Process
- **Status**: ✅ Correct
- **Reindex Script**: Uses `InfinityEmbeddings.embed_documents()` ✅
- **Index Building**: Uses `InfinityEmbeddings` for both indexing and retrieval ✅
- **Normalization**: L2 normalization applied before creating `IndexFlatIP` ✅

### 4. Query Expansion (NEW - 2024-12-19)
- **Status**: ✅ Implemented
- **Function**: `expand_ltc_entities()` in `backend/utils/litecoin_vocabulary.py`
- **Integration**: Applied in both `aquery()` and `astream_query()` methods
- **Example**: "explain litvm" → "explain litvm litecoin virtual machine zero-knowledge omnichain smart contracts"

## Historical Analysis (For Reference)

### Original Problem: Low Semantic Similarity
- **Query**: "explain litvm"
- **Best LitVM Document**: Rank 422, Score 0.291
- **Threshold**: 0.3 (lowered to 0.28)
- **Retrieval Limit**: Top 24 documents (RETRIEVER_K * 2)

**Why LitVM documents ranked low:**
1. **Query was generic**: "explain litvm" didn't contain specific technical terms
2. **Document structure**: LitVM documents have prepended metadata that dilutes semantic signal
3. **Embedding mismatch**: BGE-M3 prioritizes semantic meaning over keyword matching

### Root Cause
1. **Semantic Embedding Limitations**: Query "explain litvm" is semantically generic
2. **Document Structure**: Prepended metadata dilutes embedding signal
3. **Keyword vs Semantic Mismatch**: BM25 didn't prioritize rare entity "litvm"

## Solutions Applied

### Immediate Fixes
1. ✅ **Lowered similarity threshold**: 0.3 → 0.28
2. ✅ **Fixed index type**: L2 → InnerProduct
3. ✅ **Reindexed with correct settings**: All 2,107 documents re-embedded
4. ✅ **Query Expansion**: Appends synonyms for rare entities (NEW)

### Files Modified
- `backend/utils/litecoin_vocabulary.py` - Added `LTC_ENTITY_EXPANSIONS` and `expand_ltc_entities()`
- `backend/rag_pipeline.py` - Integrated expansion in `aquery()` and `astream_query()`

## Verification

```bash
# Test query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "explain litvm"}'

# Expected: LitVM documents in top results with high similarity scores
# Result: ✅ Working as of 2024-12-19
```

## Conclusion

The retrieval problem for rare entities like "litvm" has been **RESOLVED** through query expansion. The system now:
1. Detects rare entities in queries
2. Appends synonyms to improve semantic matching
3. Successfully retrieves relevant documents within the top 24 candidates
