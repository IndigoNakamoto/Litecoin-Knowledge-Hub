# MongoDB Connection Flow Diagram

## Connection Creation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION STARTUP                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   FastAPI App Initialization        │
        │   (main.py:115)                     │
        └─────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
    ┌───────────────────────┐   ┌───────────────────────┐
    │  RAGPipeline()        │   │  Background Task      │
    │  (main.py:149)        │   │  (main.py:105)        │
    └───────────────────────┘   └───────────────────────┘
                │                           │
                ▼                           ▼
    ┌───────────────────────┐   ┌───────────────────────┐
    │ VectorStoreManager()  │   │ Health Checker        │
    │                       │   │ (every 60s)           │
    └───────────────────────┘   └───────────────────────┘
                │                           │
                ▼                           ▼
    ┌───────────────────────┐   ┌───────────────────────┐
    │ NEW MongoClient       │   │ VectorStoreManager()  │
    │ Pool: min=10, max=50  │   │ (lazy init)           │
    └───────────────────────┘   └───────────────────────┘
                │                           │
                │                           ▼
                │               ┌───────────────────────┐
                │               │ NEW MongoClient       │
                │               │ Pool: min=10, max=50  │
                │               └───────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│              ROUTER INITIALIZATION                              │
└─────────────────────────────────────────────────────────────────┘
                │
        ┌───────┴───────┐
        │               │
        ▼               ▼
┌───────────────┐  ┌──────────────────────┐
│ Sources API   │  │ Dependencies Module  │
│ Router        │  │                      │
└───────────────┘  └──────────────────────┘
        │                   │
        ▼                   ▼
┌───────────────┐  ┌──────────────────────┐
│ get_mongo_    │  │ get_mongo_client()   │
│ client()      │  │ (lazy init)          │
│ (lazy init)   │  └──────────────────────┘
└───────────────┘           │
        │                   ▼
        ▼           ┌──────────────────────┐
┌───────────────┐   │ NEW AsyncIOMotorClient│
│ NEW MongoClient│   │ Pool: defaults       │
│ Pool: min=10,  │   └──────────────────────┘
│      max=50    │
└───────────────┘
```

## Per-Request Connection Flow (Payload Webhooks)

```
┌─────────────────────────────────────────────────────────────────┐
│              PAYLOAD WEBHOOK RECEIVED                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   process_payload_webhook()         │
        │   (api/v1/sync/payload.py:140)      │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   VectorStoreManager()              │
        │   ⚠️ NEW INSTANCE PER REQUEST       │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   NEW MongoClient                   │
        │   Pool: min=10, max=50              │
        │   ⚠️ NEW CONNECTION POOL            │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   Operations Performed              │
        │   - Document embedding              │
        │   - Vector store updates            │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   Function Returns                  │
        │   Instance goes out of scope        │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   ⚠️ NO EXPLICIT CLEANUP            │
        │   Connection pool persists          │
        │   GC eventually cleans up           │
        └─────────────────────────────────────┘
```

## Connection Pool Accumulation

```
Time: T0 (Startup)
├── Motor Client: 0 connections (lazy)
├── Sources PyMongo: 0 connections (lazy)
├── RAGPipeline VectorStore: 10 connections (minPoolSize)
└── Health Checker VectorStore: 0 connections (lazy)
    Total: ~10 connections

Time: T1 (First Request)
├── Motor Client: ~5 connections (active)
├── Sources PyMongo: 10 connections (minPoolSize)
├── RAGPipeline VectorStore: 10 connections
└── Health Checker VectorStore: 10 connections (first check)
    Total: ~35 connections

Time: T2 (Webhook Burst - 3 concurrent)
├── Motor Client: ~5 connections
├── Sources PyMongo: 10 connections
├── RAGPipeline VectorStore: 10 connections
├── Health Checker VectorStore: 10 connections
├── Webhook 1 VectorStore: 10 connections ⚠️ NEW
├── Webhook 2 VectorStore: 10 connections ⚠️ NEW
└── Webhook 3 VectorStore: 10 connections ⚠️ NEW
    Total: ~65 connections

Time: T3 (After Webhooks Complete)
├── Motor Client: ~5 connections
├── Sources PyMongo: 10 connections
├── RAGPipeline VectorStore: 10 connections
├── Health Checker VectorStore: 10 connections
├── Webhook 1 VectorStore: 10 connections ⚠️ STILL ACTIVE
├── Webhook 2 VectorStore: 10 connections ⚠️ STILL ACTIVE
└── Webhook 3 VectorStore: 10 connections ⚠️ STILL ACTIVE
    Total: ~65 connections (pools persist until GC)
```

## Connection Leak Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    CONNECTION LEAK CYCLE                    │
└─────────────────────────────────────────────────────────────┘

1. Webhook Arrives
   └──> Create VectorStoreManager()
        └──> Create MongoClient (pool: 10 connections)
             └──> Perform operations
                  └──> Function returns
                       └──> Instance out of scope
                            └──> ⚠️ Pool NOT closed
                                 └──> Connections persist

2. Next Webhook Arrives
   └──> Create NEW VectorStoreManager()
        └──> Create NEW MongoClient (pool: 10 connections)
             └──> ⚠️ Previous pool still active
                  └──> Total: 20 connections

3. Pattern Repeats
   └──> Each webhook adds 10+ connections
        └──> Pools accumulate
             └──> GC eventually cleans up (unpredictable)
                  └──> Connection churn in logs
```

## Cleanup Flow (Current - Missing)

```
┌─────────────────────────────────────────────────────────────┐
│              APPLICATION SHUTDOWN                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   FastAPI Lifespan Shutdown         │
        │   (main.py:108-113)                 │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   Cancel Background Task            │
        │   ✅ Implemented                    │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   ❌ NO MongoDB Cleanup             │
        │   - Motor client not closed         │
        │   - PyMongo clients not closed      │
        │   - VectorStoreManager pools open   │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   Process Terminates                │
        │   Connections closed by OS          │
        └─────────────────────────────────────┘
```

## Recommended Cleanup Flow

```
┌─────────────────────────────────────────────────────────────┐
│              APPLICATION SHUTDOWN                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   FastAPI Lifespan Shutdown         │
        └─────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
    ┌───────────────────────┐   ┌───────────────────────┐
    │ Cancel Background     │   │ Close MongoDB Clients │
    │ Task                  │   │                       │
    └───────────────────────┘   └───────────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
        ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
        │ Close Motor       │  │ Close Sources     │  │ Close VectorStore │
        │ Client            │  │ PyMongo Client    │  │ Manager Clients   │
        │                   │  │                   │  │                   │
        │ dependencies.py   │  │ sources.py        │  │ All instances     │
        └───────────────────┘  └───────────────────┘  └───────────────────┘
                    │                     │                     │
                    └─────────────────────┼─────────────────────┘
                                          │
                                          ▼
                            ┌─────────────────────────┐
                            │ All Connections Closed  │
                            │ Clean Shutdown          │
                            └─────────────────────────┘
```

## Connection Pool Sharing (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│              SHARED CONNECTION POOL ARCHITECTURE            │
└─────────────────────────────────────────────────────────────┘

Application Level
        │
        ▼
┌───────────────────────────────────────┐
│   Global MongoClient Singleton        │
│   Pool: min=10, max=50                │
│   (vector_store_manager.py)           │
└───────────────────────────────────────┘
        │
        ├──────────────────┬──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ RAGPipeline  │  │ Health       │  │ Payload      │
│              │  │ Checker      │  │ Sync         │
│              │  │              │  │ Endpoints    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
        └──────────────────┴──────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Single Connection   │
              │   Pool (10-50 conns)  │
              │   Shared by All       │
              └───────────────────────┘
```

---

**Legend:**
- ✅ = Implemented
- ❌ = Missing/Not Implemented
- ⚠️ = Issue/Problem
- ──> = Flow direction
- │ = Connection/Relationship

