# UnboundLocalError Fix in RAG Pipeline

**Date**: 2025-12-07  
**Status**: ✅ Fixed

---

## Issue

The `aquery` method in `backend/rag_pipeline.py` was raising `UnboundLocalError` when using Infinity embeddings:

```
UnboundLocalError: cannot access local variable 'result' where it is not associated with a value
```

**Error location**: Line 970 in `backend/rag_pipeline.py`

---

## Root Cause

When `USE_INFINITY_EMBEDDINGS=true`, the code path used `answer_result` from `document_chain.ainvoke()`, but token extraction code at line 970 referenced `result`, which was only defined in the legacy `else` branch (when using `rag_chain.ainvoke()`).

**Problematic code**:
```python
if USE_INFINITY_EMBEDDINGS and query_vector is not None:
    # Uses answer_result, not result
    answer_result = await self.document_chain.ainvoke(...)
    ...
else:
    # result only defined here
    result = await self.rag_chain.ainvoke(...)
    ...

# Later code tried to use result.get("answer")
# which didn't exist in the Infinity path
answer_obj = result.get("answer")  # ❌ UnboundLocalError
```

---

## Solution

Created a unified `llm_result` variable that is set in both code paths:

```python
if USE_INFINITY_EMBEDDINGS and query_vector is not None:
    answer_result = await self.document_chain.ainvoke(...)
    ...
    llm_result = answer_result  # ✅ Set for token extraction
else:
    result = await self.rag_chain.ainvoke(...)
    ...
    llm_result = result.get("answer", answer)  # ✅ Set for token extraction

# Token extraction now works for both paths
input_tokens, output_tokens = self._extract_token_usage_from_llm_response(llm_result)
```

---

## Changes Made

**File**: `backend/rag_pipeline.py`

1. **Line 931**: Added `llm_result = answer_result` in Infinity path
2. **Line 947**: Added `llm_result = result.get("answer", answer)` in legacy path
3. **Line 974**: Changed from `result.get("answer")` to `llm_result`

---

## Impact

- **Severity**: High (prevented all queries when using Infinity embeddings)
- **Affected**: All users with `USE_INFINITY_EMBEDDINGS=true`
- **Fix Time**: Immediate (code fix + backend restart)

---

## Testing

After the fix:
- ✅ Queries with Infinity embeddings work correctly
- ✅ Token extraction works for both code paths
- ✅ No regression in legacy path behavior

---

## Status

✅ **Fixed** - Applied in commit and deployed to production.

---

**Related Issues**:
- Embedding model configuration: See `docs/fixes/EMBEDDING_MODEL_UPDATE.md`
- Local RAG deployment: See `docs/DEPLOYMENT.md#local-rag-deployment`

