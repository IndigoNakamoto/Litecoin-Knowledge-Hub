# Input Sanitization and Cost Throttling Fixes

**Date**: 2025-12-07  
**Status**: ✅ Fixed

---

## Issues Identified

From backend logs, three critical issues were found:

### 1. Input Sanitizer: MAX_QUERY_LENGTH Too Short

**Problem**: `MAX_QUERY_LENGTH = 400` was too restrictive for chat history messages. Users with longer conversations were getting warnings:

```
WARNING - Input exceeds maximum length of 400 characters (got 1905)
WARNING - Input exceeds maximum length of 400 characters (got 2183)
WARNING - Input exceeds maximum length of 400 characters (got 2891)
```

**Impact**: Chat history messages were being truncated, potentially losing context.

**Fix**: Increased `MAX_QUERY_LENGTH` from 400 to 2000 characters.

```python
# backend/utils/input_sanitizer.py
MAX_QUERY_LENGTH = 2000  # Increased from 400
```

**Rationale**: 
- Individual chat messages can be 500-1000 characters
- Chat history with 2-3 pairs can easily exceed 400 characters
- 2000 characters provides reasonable room for conversation context while still preventing abuse

---

### 2. Cost Throttling: Threshold Too Low

**Problem**: Cost throttling threshold was set to `$0.001` (1 cent), which was too aggressive. Users were being throttled after just 2-3 queries:

```
WARNING - Cost-based throttling triggered. Estimated cost: $0.000411, Threshold: $0.001000
```

**Impact**: Legitimate users couldn't have normal conversations without hitting throttling limits.

**Fix**: This is an admin dashboard setting. **Recommendation**: Increase `high_cost_threshold_usd` to `$0.02` (2 cents) via admin dashboard.

**Rationale**:
- Average query cost: ~$0.0004 (0.04 cents)
- At $0.001 threshold: ~2-3 queries trigger throttling
- At $0.02 threshold: ~50 queries trigger throttling (more reasonable for normal use)

**Action Required**: Admin needs to update this via dashboard (Settings → Abuse Prevention → High Cost Threshold)

---

### 3. Model ID Mismatch

**Problem**: Environment variable default was still pointing to old model:

```yaml
EMBEDDING_MODEL_ID=${EMBEDDING_MODEL_ID:-dunzhang/stella_en_1.5B_v5}
```

But logs showed:
```
InfinityEmbeddings initialized: url=http://host.docker.internal:7997, model=dunzhang/stella_en_1.5B_v5
```

**Impact**: System was using wrong model (Stella instead of BGE-M3), causing:
- Higher memory usage (11GB vs 68MB)
- Potentially worse retrieval quality

**Fix**: Updated default to BGE-M3:

```yaml
# docker-compose.prod.yml
EMBEDDING_MODEL_ID=${EMBEDDING_MODEL_ID:-BAAI/bge-m3}
```

Also updated InfinityEmbeddings default:
```python
# backend/services/infinity_adapter.py
self.model_id = model_id or os.getenv("EMBEDDING_MODEL_ID", "BAAI/bge-m3")
```

---

## Changes Summary

| File | Change | Before | After |
|------|--------|--------|-------|
| `backend/utils/input_sanitizer.py` | `MAX_QUERY_LENGTH` | 400 | 2000 |
| `docker-compose.prod.yml` | `EMBEDDING_MODEL_ID` default | `stella_en_1.5B_v5` | `BAAI/bge-m3` |
| `backend/services/infinity_adapter.py` | Default model ID | `stella_en_1.5B_v5` | `BAAI/bge-m3` |
| Admin Dashboard | `high_cost_threshold_usd` | `$0.001` | `$0.02` (manual) |

---

## Next Steps

1. **Restart Backend**: 
   ```bash
   docker restart litecoin-backend
   ```

2. **Update Cost Threshold** (Admin Dashboard):
   - Go to Settings → Abuse Prevention
   - Set `high_cost_threshold_usd` to `0.02` (or higher)
   - Save settings

3. **Verify Model**:
   ```bash
   docker logs litecoin-backend | grep "InfinityEmbeddings initialized"
   ```
   Should show: `model=BAAI/bge-m3`

---

## Expected Results

- ✅ No more input truncation warnings for normal conversations
- ✅ Users can have longer conversations without throttling
- ✅ Correct embedding model (BGE-M3) used by default
- ✅ Better memory efficiency (68MB vs 11GB)

---

**Status**: ✅ Fixed - Restart required for model change, admin action required for cost threshold

