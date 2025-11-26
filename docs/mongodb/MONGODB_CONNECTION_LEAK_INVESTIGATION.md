# MongoDB Connection Leak Investigation Report

**Date:** 2025-11-16  
**Investigator:** AI Assistant  
**Status:** Investigation Complete

## Executive Summary

This investigation identified multiple MongoDB client instances across the application, each creating their own connection pools. The primary issue is that **VectorStoreManager instances are created per-request in several endpoints**, each establishing a new MongoDB connection pool with a minimum of 10 connections. Combined with missing cleanup on shutdown and background health checks, this leads to connection churn and potential leaks.

## 1. MongoDB Client Instances Inventory

### 1.1 Backend Service - Motor Client (AsyncIOMotorClient)

**Location:** `backend/dependencies.py:18-39`

**Configuration:**
- **Client Type:** Motor (AsyncIOMotorClient) - Async MongoDB driver
- **Connection Pool Settings:** **NONE** (uses Motor defaults)
- **Pattern:** Global singleton
- **Initialization:** Lazy (on first `get_mongo_client()` call)
- **Cleanup:** **NOT IMPLEMENTED** (commented-out code at lines 82-91)

**Usage:**
- FastAPI dependencies for CMS articles (`get_cms_db()`)
- User questions collection (`get_user_questions_collection()`)
- Background metrics updates (`main.py:65`)

**Connection Pool Defaults (Motor):**
- Default `maxPoolSize`: 100
- Default `minPoolSize`: 0
- No explicit configuration means unpredictable behavior

**Issues:**
- No connection pool limits configured
- No cleanup on application shutdown
- Commented-out cleanup code suggests awareness but no implementation

---

### 1.2 Backend Service - PyMongo Client (Sources API)

**Location:** `backend/api/v1/sources.py:14-33`

**Configuration:**
- **Client Type:** PyMongo (MongoClient) - Synchronous MongoDB driver
- **Connection Pool Settings:**
  - `maxPoolSize`: 50
  - `minPoolSize`: 10
  - `maxIdleTimeMS`: 30000 (30 seconds)
  - `waitQueueTimeoutMS`: 5000
  - `serverSelectionTimeoutMS`: 5000
  - `retryWrites`: True
  - `retryReads`: True
- **Pattern:** Global singleton
- **Initialization:** Lazy (on first `get_mongo_client()` call)
- **Cleanup:** **NOT IMPLEMENTED**

**Usage:**
- Sources API endpoints (`/api/v1/sources/*`)
- Data sources collection operations
- Litecoin docs collection operations

**Issues:**
- Maintains minimum 10 connections even when idle
- No cleanup on application shutdown
- Separate pool from other PyMongo clients

---

### 1.3 Backend Service - PyMongo Client (VectorStoreManager)

**Location:** `backend/data_ingestion/vector_store_manager.py:70-79`

**Configuration:**
- **Client Type:** PyMongo (MongoClient) - Synchronous MongoDB driver
- **Connection Pool Settings:**
  - `maxPoolSize`: 50
  - `minPoolSize`: 10
  - `maxIdleTimeMS`: 30000 (30 seconds)
  - `waitQueueTimeoutMS`: 5000
  - `serverSelectionTimeoutMS`: 5000
  - `retryWrites`: True
  - `retryReads`: True
- **Pattern:** **Instance-based** (each VectorStoreManager creates its own client)
- **Initialization:** On `VectorStoreManager.__init__()`
- **Cleanup:** **NOT IMPLEMENTED** (no `close()` method)

**Usage Locations:**
1. **Global instance:** `main.py:149` - `RAGPipeline()` → creates `VectorStoreManager()`
2. **Health checker:** `monitoring/health.py:47` - Lazy initialization in `HealthChecker`
3. **Payload sync endpoints:** `api/v1/sync/payload.py:79,140,269` - **NEW INSTANCE PER REQUEST**
4. **Background tasks:** Various utility scripts

**Critical Issues:**
- **Each instance creates a new connection pool with minPoolSize=10**
- **Payload sync endpoints create new instances per webhook** (lines 79, 140, 269)
- **No cleanup means pools persist until garbage collection**
- **Health checker creates separate instance** (may be recreated on each check)

**Impact:**
- If 3 webhooks arrive simultaneously, that's 3 new VectorStoreManager instances = 30 minimum connections
- Health checker runs every 60 seconds, potentially creating new instances
- Global RAGPipeline instance maintains its own pool

---

### 1.4 Payload CMS Service - Mongoose Client

**Location:** `payload_cms/src/payload.config.ts:65-67`

**Configuration:**
- **Client Type:** Mongoose (Node.js MongoDB ODM)
- **Connection Pool Settings:** Mongoose defaults (typically maxPoolSize=10)
- **Pattern:** Application-level singleton
- **Initialization:** On Payload CMS startup
- **Cleanup:** Managed by Payload CMS lifecycle

**Usage:**
- Payload CMS database operations
- Content management operations
- Separate Docker container (IP: 172.18.0.5)

**Issues:**
- Separate service, but contributes to total connection count
- Uses default Mongoose pool settings (may need tuning)

---

## 2. Connection Creation Patterns

### 2.1 Application Startup

**Sequence:**
1. FastAPI app starts (`main.py:115`)
2. Global `RAGPipeline()` instance created (`main.py:149`)
   - Creates `VectorStoreManager()` instance
   - **Creates new MongoClient with pool (minPoolSize=10)**
3. Background metrics task starts (`main.py:105`)
   - Calls health checker every 60 seconds
   - Health checker may create `VectorStoreManager()` instance

**Initial Connections:** ~10-20 connections from startup

### 2.2 Per-Request Connections

**Payload Sync Webhooks** (`api/v1/sync/payload.py`):
- Line 79: `vector_store_manager = VectorStoreManager()` in `process_delete_task()`
- Line 140: `vector_store_manager = VectorStoreManager()` in `process_payload_webhook()`
- Line 269: `vector_store_manager = VectorStoreManager()` in `process_payload_webhook()`

**Each webhook creates:**
- New `VectorStoreManager()` instance
- New `MongoClient` with `minPoolSize=10`
- **Minimum 10 connections per webhook**

**Impact:**
- High-frequency webhooks = rapid connection pool creation
- No cleanup = pools persist until GC
- Connection IDs in logs reach 155+ indicating high churn

### 2.3 Background Tasks

**Health Checker** (`monitoring/health.py:43-47`):
- Runs every 60 seconds (`main.py:89`)
- Lazy initialization: `if self.vector_store_manager is None: self.vector_store_manager = VectorStoreManager()`
- **Creates new MongoClient if instance doesn't exist**

**Metrics Updates** (`main.py:61-80`):
- Uses Motor client from `dependencies.py`
- Called every 60 seconds
- Uses existing global singleton (no new connections)

---

## 3. Connection Leak Sources

### 3.1 Missing Cleanup on Shutdown

**Issue:** No MongoDB connection cleanup in FastAPI lifespan

**Evidence:**
- `main.py:97-113` - Lifespan only cancels background task
- `dependencies.py:82-91` - Cleanup code is commented out
- `vector_store_manager.py` - No `close()` method

**Impact:**
- Connections remain open on application restart
- Pools not properly closed
- Potential resource leaks

### 3.2 Per-Request VectorStoreManager Instances

**Issue:** Payload sync endpoints create new VectorStoreManager per request

**Evidence:**
```python
# api/v1/sync/payload.py:79
def process_delete_task(payload_id: str, operation: str):
    vector_store_manager = VectorStoreManager()  # NEW INSTANCE
    # ... operations ...
    # No cleanup - instance goes out of scope, GC eventually cleans up
```

**Impact:**
- Each webhook = new connection pool (10+ connections)
- Pools persist until garbage collection
- High webhook frequency = connection accumulation

### 3.3 Multiple Independent Connection Pools

**Issue:** Three separate PyMongo clients, each with their own pool

**Clients:**
1. `sources.py` - Global singleton (minPoolSize=10)
2. `vector_store_manager.py` - Instance-based (minPoolSize=10 per instance)
3. `dependencies.py` - Motor client (no explicit limits)

**Impact:**
- Minimum 20+ connections from backend service alone
- Each pool maintains minimum connections independently
- No connection sharing between clients

### 3.4 Health Checker Connection Management

**Issue:** Health checker creates VectorStoreManager lazily, but may recreate it

**Evidence:**
- `monitoring/health.py:46-47` - Lazy initialization
- If instance is lost/reset, new one is created
- No explicit cleanup

**Impact:**
- Potential for multiple instances if health checker is recreated
- Additional connection pool per instance

---

## 4. Log Analysis

### 4.1 Connection Pattern Analysis

**From provided logs (lines 1-341):**

**Connection Sources:**
- `172.18.0.3` - Backend service (PyMongo clients)
- `172.18.0.5` - Payload CMS (Mongoose)
- `127.0.0.1` - mongosh (manual/admin access)

**Connection Churn Indicators:**
- Connection IDs reach **155+** (high turnover)
- Connection counts fluctuate **20-40** connections
- Rapid connection creation/destruction cycles

**Sample Pattern (lines 8-15):**
```
Connection ended: conn40, conn39, conn42, conn41, conn43, conn46, conn44, conn45
Connection accepted: conn63, conn64, conn65, conn66, conn67, conn68, conn69, conn70
```

**Analysis:**
- 8 connections closed simultaneously
- 8 new connections created immediately after
- Suggests connection pool recreation or reconnection cycles

### 4.2 Connection Lifecycle

**Typical Connection Lifecycle:**
1. Connection accepted (connID assigned)
2. Client metadata logged (driver info)
3. First command received
4. Connection used for operations
5. Connection ended (after idle timeout or pool cleanup)

**Observed Issues:**
- Many connections end shortly after creation
- New connections created immediately after endings
- Suggests inefficient connection reuse

### 4.3 Connection Count Fluctuations

**Pattern:**
- Connection count ranges: 20-40 active connections
- Rapid increases during webhook processing
- Gradual decreases during idle periods
- Spikes correlate with activity

**Interpretation:**
- Multiple pools maintaining minimum connections
- New pools created during high activity
- Pools not efficiently shared or reused

---

## 5. Root Cause Analysis

### 5.1 Primary Root Cause

**Per-Request VectorStoreManager Instantiation**

The payload sync endpoints create new `VectorStoreManager()` instances for each webhook request. Each instance creates a new `MongoClient` with `minPoolSize=10`, resulting in:
- 10+ new connections per webhook
- Connection pools that persist until garbage collection
- Accumulation of unused pools during high-frequency webhooks

### 5.2 Contributing Factors

1. **No Connection Pool Sharing**
   - Three separate PyMongo clients
   - No shared connection pool mechanism
   - Each maintains independent minimum connections

2. **Missing Cleanup**
   - No shutdown handlers for MongoDB clients
   - VectorStoreManager has no `close()` method
   - Commented-out cleanup code in dependencies.py

3. **Instance-Based Connection Management**
   - VectorStoreManager creates client in `__init__`
   - No singleton pattern for the client
   - Multiple instances = multiple pools

4. **Background Task Impact**
   - Health checker may create additional instances
   - 60-second intervals create potential for accumulation
   - No connection reuse between checks

### 5.3 Impact Assessment

**Current State:**
- **Minimum connections:** ~20-30 (from global instances)
- **Per-webhook overhead:** +10 connections
- **Peak connections:** 40+ during active periods
- **Connection churn:** High (IDs reach 155+)

**Potential Issues:**
- MongoDB connection limit exhaustion (default: 65536, but practical limits lower)
- Resource waste (unused connection pools)
- Performance degradation (connection establishment overhead)
- Monitoring noise (high connection churn in logs)

---

## 6. Recommendations

### 6.1 Immediate Fixes (High Priority)

#### 6.1.1 Implement Connection Pool Sharing for VectorStoreManager

**Action:** Create a singleton MongoClient for VectorStoreManager

**Implementation:**
- Add global `_vector_store_mongo_client` in `vector_store_manager.py`
- Modify `VectorStoreManager.__init__()` to use shared client
- Ensure thread-safety for concurrent access

**Impact:** Eliminates per-instance connection pools

#### 6.1.2 Fix Per-Request VectorStoreManager Creation

**Action:** Use dependency injection or global instance for payload sync

**Implementation:**
- Create global `VectorStoreManager` instance in `main.py`
- Pass instance to payload sync endpoints via dependency injection
- Or use the global `rag_pipeline_instance.vector_store_manager`

**Impact:** Eliminates per-webhook connection pool creation

#### 6.1.3 Add Cleanup on Shutdown

**Action:** Implement MongoDB client cleanup in FastAPI lifespan

**Implementation:**
- Add cleanup functions for all MongoDB clients
- Call cleanup in `lifespan()` shutdown phase
- Add `close()` method to VectorStoreManager

**Impact:** Prevents connection leaks on restart

### 6.2 Medium Priority Improvements

#### 6.2.1 Configure Motor Client Connection Pool

**Action:** Add explicit connection pool settings to Motor client

**Implementation:**
```python
mongo_client = AsyncIOMotorClient(
    MONGO_DETAILS,
    maxPoolSize=50,
    minPoolSize=5,
    maxIdleTimeMS=30000
)
```

**Impact:** Predictable connection pool behavior

#### 6.2.2 Consolidate PyMongo Clients

**Action:** Consider using single shared PyMongo client

**Implementation:**
- Create shared client module
- Use dependency injection for all PyMongo operations
- Deprecate instance-based clients

**Impact:** Single connection pool, better resource utilization

#### 6.2.3 Health Checker Connection Reuse

**Action:** Reuse global VectorStoreManager instance in health checker

**Implementation:**
- Pass `rag_pipeline_instance.vector_store_manager` to health checker
- Remove lazy initialization
- Use existing instance

**Impact:** Eliminates health checker connection pool

### 6.3 Long-Term Improvements

#### 6.3.1 Connection Pool Monitoring

**Action:** Add metrics for connection pool usage

**Implementation:**
- Track active connections per pool
- Monitor connection creation/destruction rates
- Alert on connection limit approaches

**Impact:** Proactive leak detection

#### 6.3.2 Connection Pool Tuning

**Action:** Optimize pool sizes based on usage patterns

**Implementation:**
- Analyze connection usage patterns
- Adjust `minPoolSize` and `maxPoolSize` accordingly
- Consider connection pool per database/collection

**Impact:** Optimal resource utilization

---

## 7. Connection Flow Diagram

```
Application Startup
├── FastAPI App Starts
│   ├── RAGPipeline() created
│   │   └── VectorStoreManager() created
│   │       └── NEW MongoClient (pool: min=10, max=50)
│   │
│   └── Background Task Starts
│       └── Health Checker (every 60s)
│           └── VectorStoreManager() (lazy init)
│               └── NEW MongoClient (pool: min=10, max=50)
│
├── Sources API Router
│   └── get_mongo_client() (lazy init)
│       └── NEW MongoClient (pool: min=10, max=50)
│
└── Dependencies Module
    └── get_mongo_client() (lazy init)
        └── NEW AsyncIOMotorClient (pool: defaults)

Per-Request (Payload Webhook)
├── process_payload_webhook() called
│   └── VectorStoreManager() created
│       └── NEW MongoClient (pool: min=10, max=50)
│           └── Operations performed
│           └── Instance goes out of scope
│           └── GC eventually cleans up (pools may persist)
│
└── process_delete_task() called
    └── VectorStoreManager() created
        └── NEW MongoClient (pool: min=10, max=50)
            └── Operations performed
            └── Instance goes out of scope
            └── GC eventually cleans up (pools may persist)

Shutdown
└── NO CLEANUP
    └── All connections remain open
    └── Pools persist until process termination
```

---

## 8. Summary

### Key Findings

1. **4 separate MongoDB clients** across the application
2. **Per-request VectorStoreManager creation** in payload sync endpoints
3. **No cleanup on shutdown** for any MongoDB clients
4. **Multiple connection pools** with minimum 10 connections each
5. **High connection churn** (connection IDs reach 155+)

### Critical Issues

1. **Connection Leak:** Per-request VectorStoreManager instances create new pools that persist
2. **Resource Waste:** Multiple pools maintaining minimum connections independently
3. **No Cleanup:** Connections not properly closed on shutdown
4. **Unpredictable Scaling:** Connection count grows with webhook frequency

### Recommended Actions

1. **Immediate:** Fix per-request VectorStoreManager creation (use global instance)
2. **Immediate:** Add cleanup on shutdown for all MongoDB clients
3. **Short-term:** Implement connection pool sharing for VectorStoreManager
4. **Medium-term:** Consolidate PyMongo clients and configure Motor client pools
5. **Long-term:** Add connection pool monitoring and optimize pool sizes

---

## Appendix A: Code References

### Files Analyzed

1. `backend/dependencies.py` - Motor client (lines 18-91)
2. `backend/api/v1/sources.py` - PyMongo client (lines 14-33)
3. `backend/data_ingestion/vector_store_manager.py` - PyMongo client (lines 70-79)
4. `backend/main.py` - Application lifecycle (lines 97-149)
5. `backend/api/v1/sync/payload.py` - Per-request instances (lines 79, 140, 269)
6. `backend/monitoring/health.py` - Health checker (lines 43-47)
7. `payload_cms/src/payload.config.ts` - Mongoose client (lines 65-67)

### Connection Pool Configurations

| Client | Location | maxPoolSize | minPoolSize | maxIdleTimeMS | Cleanup |
|--------|----------|-------------|-------------|---------------|---------|
| Motor | dependencies.py | Default (100) | Default (0) | Default | ❌ None |
| PyMongo (Sources) | sources.py | 50 | 10 | 30000 | ❌ None |
| PyMongo (VectorStore) | vector_store_manager.py | 50 | 10 | 30000 | ❌ None |
| Mongoose (CMS) | payload.config.ts | Default (10) | Default | Default | ✅ Managed |

---

**End of Report**

