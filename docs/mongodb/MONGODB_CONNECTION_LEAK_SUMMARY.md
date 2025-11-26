# MongoDB Connection Leak Investigation - Executive Summary

## Quick Reference

**Investigation Date:** 2025-11-16  
**Status:** Complete  
**Severity:** Medium-High (Connection accumulation, resource waste)

## Key Findings

### Problem
MongoDB connections are accumulating due to:
1. **Per-request VectorStoreManager creation** in payload sync endpoints
2. **Multiple independent connection pools** (4 separate clients)
3. **No cleanup on shutdown**
4. **Connection pool churn** (connection IDs reach 155+)

### Root Cause
Payload sync webhooks create new `VectorStoreManager()` instances per request, each establishing a new MongoDB connection pool with minimum 10 connections. These pools persist until garbage collection, leading to connection accumulation.

### Impact
- **Current:** 20-40 active connections during normal operation
- **Peak:** 65+ connections during webhook bursts
- **Waste:** Multiple pools maintaining minimum connections independently
- **Risk:** Potential connection limit exhaustion under high load

## MongoDB Clients Identified

| Client | Location | Pool Config | Cleanup | Issue |
|--------|----------|-------------|---------|-------|
| Motor | `dependencies.py` | Defaults | ❌ None | No pool limits |
| PyMongo (Sources) | `sources.py` | min=10, max=50 | ❌ None | Separate pool |
| PyMongo (VectorStore) | `vector_store_manager.py` | min=10, max=50 | ❌ None | **Per-instance pools** |
| Mongoose (CMS) | `payload_cms/config.ts` | Defaults | ✅ Managed | Separate service |

## Critical Issues

### 1. Per-Request Connection Pool Creation
**Location:** `api/v1/sync/payload.py:79,140,269`

```python
# Each webhook creates new instance
vector_store_manager = VectorStoreManager()  # NEW MongoClient with 10+ connections
```

**Fix:** Use global instance or dependency injection

### 2. Missing Cleanup
**Locations:** All MongoDB clients

- No shutdown handlers in FastAPI lifespan
- VectorStoreManager has no `close()` method
- Commented-out cleanup code in dependencies.py

**Fix:** Implement cleanup in `lifespan()` shutdown phase

### 3. Multiple Independent Pools
**Issue:** Three separate PyMongo clients, each with own pool

**Fix:** Implement connection pool sharing for VectorStoreManager

## Recommendations Priority

### Immediate (High Priority)
1. ✅ **Fix per-request VectorStoreManager creation**
   - Use global `rag_pipeline_instance.vector_store_manager`
   - Or implement dependency injection

2. ✅ **Add cleanup on shutdown**
   - Close all MongoDB clients in FastAPI lifespan
   - Add `close()` method to VectorStoreManager

3. ✅ **Implement connection pool sharing**
   - Create singleton MongoClient for VectorStoreManager
   - Reuse across all instances

### Short-Term (Medium Priority)
4. Configure Motor client connection pool
5. Consolidate PyMongo clients
6. Reuse global VectorStoreManager in health checker

### Long-Term (Low Priority)
7. Add connection pool monitoring
8. Optimize pool sizes based on usage

## Connection Flow Summary

```
Startup:
├── RAGPipeline → VectorStoreManager → MongoClient (10 connections)
├── Health Checker → VectorStoreManager → MongoClient (10 connections)
├── Sources API → MongoClient (10 connections)
└── Dependencies → Motor Client (defaults)

Per Webhook:
└── NEW VectorStoreManager → NEW MongoClient (10 connections) ⚠️

Shutdown:
└── NO CLEANUP ❌
```

## Log Analysis Highlights

- **Connection IDs:** Reach 155+ (high churn)
- **Connection Count:** Fluctuates 20-40
- **Pattern:** Rapid creation/destruction cycles
- **Sources:** Backend (172.18.0.3), CMS (172.18.0.5), Admin (127.0.0.1)

## Files to Review

1. `docs/mongodb/MONGODB_CONNECTION_LEAK_INVESTIGATION.md` - Full investigation report
2. `docs/mongodb/MONGODB_CONNECTION_FLOW.md` - Visual connection flow diagrams
3. `backend/api/v1/sync/payload.py` - Per-request instance creation
4. `backend/data_ingestion/vector_store_manager.py` - Connection pool creation
5. `backend/main.py` - Missing cleanup in lifespan
6. `backend/dependencies.py` - Commented-out cleanup code

## Next Steps

1. Review full investigation report
2. Prioritize fixes based on impact
3. Implement immediate fixes (per-request instances, cleanup)
4. Monitor connection counts after fixes
5. Implement medium-term improvements

---

**For detailed analysis, see:** `MONGODB_CONNECTION_LEAK_INVESTIGATION.md`  
**For visual flows, see:** `MONGODB_CONNECTION_FLOW.md`

