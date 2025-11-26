# Suggested Question Response Caching Feature

## Overview

This feature implements **an additional caching layer** specifically for suggested question responses from Payload CMS. This specialized cache works **in addition to** the existing `QueryCache` system, providing pre-generated responses for suggested questions with a longer TTL and persistent storage.

**Status**: ✅ **Implemented**

**Priority**: High - Improves user experience and reduces costs

**Last Updated**: 2025-01-XX

---

## Table of Contents

1. [Feature Summary](#feature-summary)
2. [Caching Architecture](#caching-architecture)
3. [Business Requirements](#business-requirements)
4. [Technical Requirements](#technical-requirements)
5. [Implementation Details](#implementation-details)
6. [Configuration](#configuration)
7. [Cache Management](#cache-management)
8. [Monitoring & Metrics](#monitoring--metrics)
9. [API Endpoints](#api-endpoints)
10. [Testing](#testing)
11. [Deployment](#deployment)
12. [Future Enhancements](#future-enhancements)

---

## Feature Summary

### Problem Statement

Currently, when users click on suggested questions from Payload CMS:
- Each click triggers a full RAG pipeline execution (even with existing QueryCache)
- The existing `QueryCache` (1-hour TTL, in-memory) doesn't persist across restarts
- Suggested questions are frequently asked but need to be regenerated after cache expiry
- Same questions generate identical responses repeatedly, wasting LLM API calls

### Solution

A **specialized Redis-based cache layer** that:
1. **Pre-generates responses** for all active suggested questions on startup
2. **Caches responses** in Redis with 24-hour TTL (longer than QueryCache)
3. **Checks cache first** before the existing QueryCache layer
4. **Persists across restarts** (unlike in-memory QueryCache)
5. **Falls back gracefully** to existing QueryCache → RAG pipeline if cache miss

### Key Benefits

- ✅ **Instant responses** - Cached responses return in <100ms vs 2-5 seconds
- ✅ **Cost reduction** - Eliminates redundant LLM API calls for suggested questions
- ✅ **Better UX** - Users get immediate answers to common questions
- ✅ **Persistence** - Survives application restarts (unlike in-memory QueryCache)
- ✅ **Longer TTL** - 24 hours vs 1 hour for general QueryCache
- ✅ **Pre-populated** - Responses ready before first user request

---

## Caching Architecture

### Multi-Layer Cache Strategy

The system uses a **two-layer caching approach**:

```
User Query (Suggested Question)
    │
    ▼
┌─────────────────────────────────────┐
│ Layer 1: Suggested Question Cache   │  ← NEW (Redis, 24h, pre-populated)
│ - Redis-based                       │
│ - 24-hour TTL                       │
│ - Pre-generated on startup          │
│ - No chat history in key            │
└──────────────┬──────────────────────┘
               │ Cache Miss
               ▼
┌─────────────────────────────────────┐
│ Layer 2: Query Cache                │  ← EXISTING (In-memory, 1h)
│ - In-memory                         │
│ - 1-hour TTL                        │
│ - Includes chat history in key      │
│ - Populated on-demand               │
└──────────────┬──────────────────────┘
               │ Cache Miss
               ▼
┌─────────────────────────────────────┐
│ RAG Pipeline                        │  ← EXISTING
│ - Generate response via LLM         │
│ - Store in QueryCache               │
└─────────────────────────────────────┘
```

### Cache Comparison

| Feature | Suggested Question Cache | Query Cache (Existing) |
|---------|-------------------------|------------------------|
| **Storage** | Redis (persistent) | In-memory (ephemeral) |
| **TTL** | 24 hours | 1 hour |
| **Pre-population** | Yes (on startup) | No (on-demand) |
| **Cache Key** | Question text only | Question + chat history |
| **Scope** | Suggested questions only | All queries |
| **Persistence** | Survives restarts | Lost on restart |
| **Purpose** | Optimize common questions | General query optimization |

### Cache Lookup Flow

**For Suggested Questions (empty chat history)**:

1. **Check Suggested Question Cache** (Redis, 24h)
   - Normalize question text
   - Generate cache key (MD5 hash of normalized question)
   - Check Redis
   - **If hit**: Return immediately (<100ms)

2. **Check Query Cache** (In-memory, 1h) - *Existing*
   - Generate cache key (question + empty chat history)
   - Check in-memory cache
   - **If hit**: Return and optionally populate Suggested Question Cache

3. **Run RAG Pipeline** - *Existing*
   - Generate response via LLM
   - Store in QueryCache
   - Optionally store in Suggested Question Cache (if it's a suggested question)

**For Regular Queries (with chat history)**:

1. **Check Query Cache** (In-memory, 1h) - *Existing*
   - Generate cache key (question + chat history)
   - Check in-memory cache
   - **If hit**: Return

2. **Run RAG Pipeline** - *Existing*
   - Generate response via LLM
   - Store in QueryCache

---

## Business Requirements

### BR-1: Pre-cache Suggested Questions
- **Requirement**: Pre-generate and cache responses for all active suggested questions
- **Priority**: Critical
- **Acceptance Criteria**:
  - Cache is populated on application startup (before first request)
  - Only active questions (isActive=true) are cached
  - Cache generation runs in background (non-blocking)
  - Failed cache generations are logged but don't block startup
  - Works independently of existing QueryCache

### BR-2: Cache Lookup on User Queries
- **Requirement**: Check suggested question cache FIRST, before existing QueryCache
- **Priority**: Critical
- **Acceptance Criteria**:
  - Suggested question cache is checked before QueryCache
  - Cache hits return responses immediately
  - Cache misses fall through to QueryCache → RAG pipeline
  - Works for both streaming and non-streaming endpoints
  - No impact on existing QueryCache behavior

### BR-3: 24-Hour Cache TTL
- **Requirement**: Cached responses expire after 24 hours (longer than QueryCache)
- **Priority**: High
- **Acceptance Criteria**:
  - Redis TTL is set to 86400 seconds (24 hours)
  - Expired entries are automatically removed by Redis
  - Longer TTL than QueryCache (1 hour) for better persistence
  - Cache refresh can be triggered manually or on schedule

### BR-4: Persistence Across Restarts
- **Requirement**: Cache survives application restarts (unlike in-memory QueryCache)
- **Priority**: High
- **Acceptance Criteria**:
  - Cache stored in Redis (not in-memory)
  - Cache entries persist after application restart
  - No need to regenerate on every restart
  - Faster startup (can skip already-cached questions)

### BR-5: Graceful Degradation
- **Requirement**: System continues to work if Redis is unavailable
- **Priority**: High
- **Acceptance Criteria**:
  - Cache misses fall back to QueryCache → RAG pipeline
  - Redis connection errors are logged but don't crash the app
  - Users still get responses (just slower, using existing caches)
  - No impact on existing QueryCache functionality

---

## Technical Requirements

### TR-1: Redis Integration
- **Requirement**: Use Redis for persistent cache storage (separate from QueryCache)
- **Priority**: Critical
- **Details**:
  - Redis keys: `suggested_question:{md5_hash}`
  - Values: JSON-encoded response data (answer + sources)
  - TTL: 86400 seconds (24 hours)
  - Encoding: UTF-8, JSON serialization
  - Separate from existing QueryCache (which is in-memory)

### TR-2: Question Normalization
- **Requirement**: Normalize question text for consistent cache keys (no chat history)
- **Priority**: High
- **Details**:
  - Convert to lowercase
  - Strip leading/trailing whitespace
  - Collapse multiple spaces to single space
  - Generate MD5 hash for cache key
  - **Key difference**: No chat history in key (unlike QueryCache)

### TR-3: Cache Layer Ordering
- **Requirement**: Check Suggested Question Cache before QueryCache
- **Priority**: Critical
- **Details**:
  - Suggested Question Cache checked first (for empty chat history)
  - QueryCache checked second (existing behavior)
  - RAG pipeline as final fallback (existing behavior)
  - Each layer independent and can function alone

### TR-4: Source Document Serialization
- **Requirement**: Properly serialize Langchain Document objects for Redis storage
- **Priority**: High
- **Details**:
  - Convert Document objects to dict format
  - Preserve page_content and metadata
  - Filter out unpublished documents
  - Handle both Document objects and dicts
  - Compatible with existing QueryCache format

### TR-5: Streaming Response Support
- **Requirement**: Support cached responses in streaming endpoint
- **Priority**: High
- **Details**:
  - Chunk cached responses to simulate streaming
  - Maintain same SSE format as RAG pipeline
  - Include cache hit indicator in response
  - Works alongside existing QueryCache streaming

### TR-6: Payload CMS Integration
- **Requirement**: Fetch suggested questions from Payload CMS API
- **Priority**: Critical
- **Details**:
  - Use httpx for async HTTP requests
  - Fetch only active questions (isActive=true)
  - Handle timeouts and errors gracefully
  - Support configurable Payload CMS URL

---

## Implementation Details

### File Structure

```
backend/
├── cache_utils.py              # SuggestedQuestionCache class (NEW)
│   └── QueryCache              # Existing in-memory cache
│   └── SuggestedQuestionCache  # NEW Redis-based cache
├── utils/
│   └── suggested_questions.py  # Payload CMS integration (NEW)
├── main.py                     # Cache refresh + endpoint updates
└── rag_pipeline.py             # Existing (uses QueryCache)
```

### Cache Lookup Implementation

**In `main.py` chat endpoints**:

```python
# Check Suggested Question Cache FIRST (for empty chat history)
if len(request.chat_history) == 0:
    cached_result = await suggested_question_cache.get(request.query)
    if cached_result:
        # Cache hit - return immediately
        return cached_result

# Fall through to existing QueryCache (in RAG pipeline)
# RAG pipeline will check QueryCache internally
answer, sources = await rag_pipeline_instance.aquery(request.query, paired_chat_history)
```

**In `rag_pipeline.py`** (existing, unchanged):

```python
# Existing QueryCache check (unchanged)
cached_result = query_cache.get(query_text, truncated_history)
if cached_result:
    return cached_result

# RAG pipeline execution...
```

### Key Classes

#### `SuggestedQuestionCache` (NEW)

```python
class SuggestedQuestionCache:
    """
    Redis-based cache for suggested question responses with 24-hour TTL.
    This is an ADDITIONAL cache layer on top of the existing QueryCache.
    """
    
    def __init__(self, ttl_seconds: int = 86400)
    async def get(question: str) -> Optional[Tuple[str, List]]
    async def set(question: str, answer: str, sources: List) -> None
    async def is_cached(question: str) -> bool
    async def clear() -> None
```

**Key Differences from QueryCache**:
- Uses Redis (persistent) vs in-memory
- 24-hour TTL vs 1-hour TTL
- No chat history in cache key
- Pre-populated on startup
- Async operations (Redis is async)

#### `QueryCache` (EXISTING - Unchanged)

```python
class QueryCache:
    """
    In-memory cache for query responses with TTL and size limits.
    This is the EXISTING cache that continues to work as before.
    """
    # Existing implementation unchanged
```

### Redis Key Schema

```
# Suggested question cache (NEW)
suggested_question:{md5_hash} → {
  "answer": "Full response text...",
  "sources": [
    {
      "page_content": "...",
      "metadata": {...}
    }
  ],
  "question": "Original question text",
  "cached_at": 1704067200.0
} (JSON, TTL: 86400s)

# QueryCache keys (EXISTING - in-memory, not Redis)
# Format: MD5 hash of {query + chat_history}
# Stored in Python dict, not Redis
```

### Cache Population Flow

**On Startup**:

```
Application Startup
    │
    ▼
Background Task: refresh_suggested_question_cache()
    │
    ├─→ Fetch questions from Payload CMS
    │
    ├─→ For each question:
    │   ├─→ Check if already cached in Redis
    │   ├─→ If not cached:
    │   │   ├─→ Generate response via RAG (empty history)
    │   │   └─→ Store in Suggested Question Cache (Redis)
    │   └─→ If cached: Skip (already exists)
    │
    └─→ Log statistics
```

**Note**: This runs independently of QueryCache. QueryCache continues to populate on-demand as before.

**Scheduled Refresh (Cron Job - Every 48 Hours)**:

```
Cron Job Trigger (2:00 AM UTC every 2 days)
    │
    ▼
POST /api/v1/admin/refresh-suggested-cache
    │
    ▼
refresh_suggested_question_cache()
    │
    ├─→ Fetch all active questions from Payload CMS
    │
    ├─→ For each question:
    │   ├─→ Generate response via RAG (empty history)
    │   ├─→ Overwrite existing cache entry (if any)
    │   └─→ Store in Suggested Question Cache (Redis)
    │       └─→ Set TTL to 24 hours (resets expiration)
    │
    └─→ Log statistics (cached, errors, duration)
```

**Key Points**:
- Runs every 48 hours via cron job (scheduled at 2:00 AM UTC every 2 days by default)
- **Overwrites** all existing cache entries (ensures freshness)
- Resets TTL to 24 hours for all entries (cache refreshed every 48h, TTL is 24h for safety margin)
- Prevents cache expiration by refreshing before TTL expires
- Runs independently of QueryCache (which continues normal operation)
- Can be triggered manually via admin endpoint if needed

### Error Handling

**Redis Unavailable**:
- Log error but don't crash
- Return `None` from cache get operations
- Fall back to QueryCache → RAG pipeline automatically
- Existing QueryCache continues to work (in-memory)

**Payload CMS Unavailable**:
- Log error during cache refresh
- Continue with existing cache entries in Redis
- Don't block application startup
- QueryCache unaffected

**Cache Generation Failures**:
- Log error for individual question failures
- Continue processing other questions
- Track error count in logs
- QueryCache continues to work normally

**Cron Job Failures**:
- Cron job failures are logged to configured log file
- Failed refresh attempts don't affect existing cache entries
- Cache continues to serve existing entries until next successful refresh
- Consider alerting/monitoring for consecutive cron job failures
- Manual refresh can be triggered if cron job fails
- QueryCache continues to work normally (independent system)

---

## Configuration

### Environment Variables

Add to `backend/.env`:

```bash
# Payload CMS URL (default: https://cms.lite.space)
PAYLOAD_URL=https://cms.lite.space

# Alternative: Use PAYLOAD_PUBLIC_SERVER_URL if already set
# PAYLOAD_PUBLIC_SERVER_URL=https://cms.lite.space

# Redis URL (default: redis://redis:6379/0)
# NOTE: This is the same Redis used for rate limiting
REDIS_URL=redis://redis:6379/0

# Cache TTL in seconds (default: 86400 = 24 hours)
SUGGESTED_QUESTION_CACHE_TTL=86400
```

**Note**: The existing `QueryCache` configuration (in-memory, 1-hour TTL) remains unchanged and continues to work independently.

### Configuration by Environment

| Environment | Suggested Cache TTL | Query Cache TTL | Refresh Strategy |
|-------------|-------------------|-----------------|------------------|
| Development | 1 hour | 1 hour (existing) | Manual only |
| Staging | 24 hours | 1 hour (existing) | On startup + cron (24h) + manual |
| Production | 24 hours | 1 hour (existing) | On startup + cron (24h) + webhook |

---

## Cache Management

### Automatic Refresh

**On Startup**:
- Suggested Question Cache refresh runs in background (non-blocking)
- Fetches all active questions from Payload CMS
- Generates responses for uncached questions
- Logs progress and statistics
- **Independent of QueryCache** (which continues to work on-demand)

**Scheduled Refresh (Cron Job)**:
- **Frequency**: Runs every 24 hours via cron job
- **Purpose**: Refreshes all cached entries before they expire (24-hour TTL, refreshed every 48 hours)
- **Implementation**: Cron job triggers cache refresh endpoint or direct function call
- **Timing**: Recommended to run at off-peak hours (e.g., 2:00 AM UTC)
- **Behavior**: 
  - Fetches all active questions from Payload CMS
  - Regenerates responses for all questions (overwrites existing cache)
  - Ensures cache is always fresh and never expires
  - Logs progress and statistics
- **Independence**: QueryCache continues its normal operation (unaffected)

### Manual Refresh

**Admin Endpoint** (Future Enhancement):
```
POST /api/v1/admin/refresh-suggested-cache
Authorization: Bearer {admin_token}

Response:
{
  "status": "success",
  "cached": 15,
  "skipped": 3,
  "errors": 0,
  "total": 18
}
```

**Note**: This only refreshes the Suggested Question Cache. QueryCache continues to operate independently.

### Grafana Quick Reference

**Common Queries for Troubleshooting**:

1. **Check if cache is being used**:
   ```promql
   sum(rate(suggested_question_cache_hits_total[5m])) + sum(rate(suggested_question_cache_misses_total[5m]))
   ```
   Should be > 0 if cache is being queried

2. **Check current cache size**:
   ```promql
   suggested_question_cache_size
   ```
   Should match number of active suggested questions

3. **Check last cache refresh time**:
   ```promql
   time() - suggested_question_cache_refresh_duration_seconds_count
   ```
   Should show when last refresh occurred

4. **Compare cache performance**:
   ```promql
   # Suggested Cache Hit Rate
   ((sum(rate(suggested_question_cache_hits_total[5m])) or vector(0)) / clamp_min(((sum(rate(suggested_question_cache_hits_total[5m])) or vector(0)) + (sum(rate(suggested_question_cache_misses_total[5m])) or vector(0))), 1))
   
   # Query Cache Hit Rate
   ((sum(rate(rag_cache_hits_total[5m])) or vector(0)) / clamp_min(((sum(rate(rag_cache_hits_total[5m])) or vector(0)) + (sum(rate(rag_cache_misses_total[5m])) or vector(0))), 1))
   ```
   Run both queries side-by-side to compare performance

### Cache Interaction

**When Suggested Question is Asked**:

1. **Normal Operation** (cache refreshed by cron every 24h):
   - Suggested Question Cache: ✅ Hit → Return immediately
   - Cache is refreshed daily before expiration, so hits are expected

2. **If Cron Job Fails** (cache expires after 24h):
   - Suggested Question Cache: ❌ Miss (expired)
   - QueryCache: ✅ Hit (if within 1 hour) → Return
   - QueryCache: ❌ Miss → RAG Pipeline → Store in QueryCache

3. **After Both Caches Expire** (rare, only if cron fails):
   - Suggested Question Cache: ❌ Miss
   - QueryCache: ❌ Miss
   - RAG Pipeline: Generate → Store in QueryCache

**Note**: With the 48-hour cron job refresh, the cache is refreshed every 2 days, which is well before the 24-hour TTL expires. This provides a safety margin - even if the cron job is delayed by a day, the cache will still be valid. Expiration only occurs if the cron job fails for more than 24 hours.

---

## Monitoring & Metrics

### Prometheus Metrics

**Suggested Question Cache** (NEW):
```python
suggested_question_cache_hits_total{cache_type="suggested_question"}  # Counter
suggested_question_cache_misses_total{cache_type="suggested_question"}  # Counter
suggested_question_cache_lookup_duration_seconds  # Histogram
suggested_question_cache_size  # Gauge (number of cached questions)
suggested_question_cache_refresh_duration_seconds  # Histogram
suggested_question_cache_refresh_errors_total  # Counter
```

**Query Cache** (EXISTING - unchanged):
```python
rag_cache_hits_total{cache_type="query"}  # Counter (existing)
rag_cache_misses_total{cache_type="query"}  # Counter (existing)
```

### Cache Hit Rate Analysis

**Expected Behavior**:
- **Suggested Question Cache**: High hit rate for suggested questions (80-95%)
- **QueryCache**: High hit rate for repeated queries within 1 hour (60-80%)
- **Combined**: Very high overall cache hit rate (90%+)

### Grafana Integration

The Suggested Question Cache metrics are fully integrated with the existing Grafana monitoring infrastructure. Metrics are automatically collected by Prometheus and can be visualized in Grafana dashboards.

#### Dashboard Panels

Add the following panels to your Grafana dashboard (`monitoring/grafana/dashboards/litecoin-knowledge-hub.json`) to monitor Suggested Question Cache performance:

**1. Suggested Question Cache Hit Rate** (Stat Panel):
```promql
((sum(rate(suggested_question_cache_hits_total[5m])) or vector(0)) / clamp_min(((sum(rate(suggested_question_cache_hits_total[5m])) or vector(0)) + (sum(rate(suggested_question_cache_misses_total[5m])) or vector(0))), 1))
```
- **Panel Type**: Stat
- **Unit**: percentunit (0-1)
- **Thresholds**: Green (>0.8), Yellow (0.5-0.8), Red (<0.5)
- **Description**: Shows the percentage of cache hits vs misses for suggested questions

**2. Cache Hit/Miss Rate Over Time** (Time Series):
```promql
# Hits
sum(rate(suggested_question_cache_hits_total[5m])) by (cache_type)

# Misses
sum(rate(suggested_question_cache_misses_total[5m])) by (cache_type)
```
- **Panel Type**: Time Series
- **Unit**: reqps (requests per second)
- **Description**: Shows the rate of cache hits and misses over time

**3. Combined Cache Hit Rate** (Time Series):
```promql
# Suggested Question Cache Hit Rate
((sum(rate(suggested_question_cache_hits_total[5m])) or vector(0)) / clamp_min(((sum(rate(suggested_question_cache_hits_total[5m])) or vector(0)) + (sum(rate(suggested_question_cache_misses_total[5m])) or vector(0))), 1))

# Query Cache Hit Rate (existing)
((sum(rate(rag_cache_hits_total[5m])) or vector(0)) / clamp_min(((sum(rate(rag_cache_hits_total[5m])) or vector(0)) + (sum(rate(rag_cache_misses_total[5m])) or vector(0))), 1))
```
- **Panel Type**: Time Series
- **Unit**: percentunit
- **Legend**: "Suggested Cache" and "Query Cache"
- **Description**: Compare hit rates between both cache layers

**4. Cache Size** (Stat Panel):
```promql
suggested_question_cache_size
```
- **Panel Type**: Stat
- **Unit**: short (number)
- **Description**: Current number of cached suggested questions

**5. Cache Lookup Duration** (Time Series):
```promql
histogram_quantile(0.95, rate(suggested_question_cache_lookup_duration_seconds_bucket[5m]))
histogram_quantile(0.50, rate(suggested_question_cache_lookup_duration_seconds_bucket[5m]))
```
- **Panel Type**: Time Series
- **Unit**: seconds
- **Legend**: "P95" and "P50"
- **Description**: Shows cache lookup performance (should be <100ms)

**6. Cache Refresh Duration** (Time Series):
```promql
histogram_quantile(0.95, rate(suggested_question_cache_refresh_duration_seconds_bucket[5m]))
histogram_quantile(0.50, rate(suggested_question_cache_refresh_duration_seconds_bucket[5m]))
```
- **Panel Type**: Time Series
- **Unit**: seconds
- **Legend**: "P95" and "P50"
- **Description**: Shows how long cache refresh operations take (cron job performance)

**7. Cache Refresh Errors** (Stat Panel):
```promql
sum(rate(suggested_question_cache_refresh_errors_total[5m]))
```
- **Panel Type**: Stat
- **Unit**: reqps
- **Thresholds**: Green (=0), Red (>0)
- **Description**: Rate of errors during cache refresh operations

**8. Cache Refresh Success Rate** (Time Series):
```promql
# Successful refreshes (inferred from refresh duration being recorded)
sum(rate(suggested_question_cache_refresh_duration_seconds_count[5m]))

# Errors
sum(rate(suggested_question_cache_refresh_errors_total[5m]))
```
- **Panel Type**: Time Series
- **Unit**: reqps
- **Legend**: "Successful" and "Errors"
- **Description**: Track successful vs failed cache refresh operations

#### Recommended Dashboard Layout

Add a new row section titled **"Suggested Question Cache Performance"** with the following panels:

```
Row: Suggested Question Cache Performance
├── Panel 1: Suggested Question Cache Hit Rate (Stat, 6x4)
├── Panel 2: Cache Size (Stat, 6x4)
├── Panel 3: Cache Hit/Miss Rate Over Time (Time Series, 12x6)
├── Panel 4: Combined Cache Hit Rate Comparison (Time Series, 12x6)
├── Panel 5: Cache Lookup Duration (Time Series, 12x6)
├── Panel 6: Cache Refresh Duration (Time Series, 12x6)
└── Panel 7: Cache Refresh Errors (Stat, 6x4)
```

#### PromQL Query Examples

**Cache Hit Rate (5-minute window)**:
```promql
((sum(rate(suggested_question_cache_hits_total[5m])) or vector(0)) / clamp_min(((sum(rate(suggested_question_cache_hits_total[5m])) or vector(0)) + (sum(rate(suggested_question_cache_misses_total[5m])) or vector(0))), 1))
```

**Total Cache Hits (last 24 hours)**:
```promql
sum(increase(suggested_question_cache_hits_total[24h]))
```

**Total Cache Misses (last 24 hours)**:
```promql
sum(increase(suggested_question_cache_misses_total[24h]))
```

**Average Cache Lookup Time**:
```promql
rate(suggested_question_cache_lookup_duration_seconds_sum[5m]) / rate(suggested_question_cache_lookup_duration_seconds_count[5m])
```

**Cache Refresh Frequency** (should show spikes every 24 hours):
```promql
sum(rate(suggested_question_cache_refresh_duration_seconds_count[1h]))
```

**Cost Savings Estimate** (cache hits that avoided LLM calls):
```promql
# Estimated cost saved per hour (assuming $0.001 per LLM call)
sum(rate(suggested_question_cache_hits_total[1h])) * 3600 * 0.001
```

#### Alerting Rules

Add to `monitoring/alerts.yml`:

```yaml
- alert: LowSuggestedQuestionCacheHitRate
  expr: |
    ((sum(rate(suggested_question_cache_hits_total[5m])) or vector(0)) / 
     clamp_min(((sum(rate(suggested_question_cache_hits_total[5m])) or vector(0)) + 
                (sum(rate(suggested_question_cache_misses_total[5m])) or vector(0))), 1)) < 0.5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Suggested Question Cache hit rate is below 50%"
    description: "Cache hit rate is {{ $value | humanizePercentage }}, expected >80%"

- alert: SuggestedQuestionCacheRefreshFailed
  expr: |
    sum(rate(suggested_question_cache_refresh_errors_total[5m])) > 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Suggested Question Cache refresh is failing"
    description: "Cache refresh errors detected at {{ $value }} errors/sec"

- alert: SuggestedQuestionCacheSizeZero
  expr: |
    suggested_question_cache_size == 0
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Suggested Question Cache is empty"
    description: "Cache size is 0, cache may not be populating correctly"
```

#### Accessing Grafana

1. **Start Monitoring Stack**:
   ```bash
   docker-compose -f monitoring/docker-compose.monitoring.yml up -d
   ```

2. **Access Grafana**:
   - URL: http://localhost:3002
   - Default credentials: `admin` / `admin`

3. **View Dashboard**:
   - Navigate to: Dashboards → Litecoin Knowledge Hub - Monitoring Dashboard
   - The Suggested Question Cache panels will appear once metrics are being collected

4. **Verify Metrics Collection**:
   - Check Prometheus: http://localhost:9090
   - Query: `suggested_question_cache_hits_total`
   - Should return metric data if cache is being used

### Logging

**Cache Operations**:
- INFO: Suggested Question Cache refresh started/completed
- INFO: Cron job triggered cache refresh
- DEBUG: Individual question cache operations
- WARNING: Redis unavailable, falling back to QueryCache
- WARNING: Cron job refresh failed (with error details)
- ERROR: Cache generation failures
- ERROR: Cron job execution errors

**Example Log Messages**:
```
# Startup refresh
INFO: Starting suggested question cache refresh...
INFO: Fetched 18 suggested questions from Payload CMS
INFO: Cached response for question: What is Litecoin and how does it differ from Bitcoin?
INFO: Suggested question cache refresh complete. Cached: 15, Skipped: 3, Errors: 0, Total: 18

# Cron job refresh (every 24 hours)
INFO: [Cron] Starting scheduled suggested question cache refresh...
INFO: [Cron] Fetched 18 active questions from Payload CMS
INFO: [Cron] Refreshing cache for 18 questions...
INFO: [Cron] Suggested question cache refresh complete. Refreshed: 18, Errors: 0, Duration: 45.2s

# Cache hits
DEBUG: Suggested Question Cache hit for: "what is litecoin?"
DEBUG: QueryCache miss (falling back to RAG pipeline)

# Cron job failures
WARNING: [Cron] Suggested question cache refresh failed: Connection timeout to Payload CMS
ERROR: [Cron] Failed to refresh suggested question cache after 3 retries
```

---

## API Endpoints

### Existing Endpoints (Modified)

#### `POST /api/v1/chat`

**Changes**:
- **NEW**: Checks Suggested Question Cache FIRST (when chat_history is empty)
- **EXISTING**: Falls through to QueryCache (checked in RAG pipeline)
- **EXISTING**: Falls through to RAG pipeline if both caches miss

**Request**:
```json
{
  "query": "What is Litecoin?",
  "chat_history": []
}
```

**Response Flow**:
1. Check Suggested Question Cache → ✅ Hit → Return immediately
2. If miss: Check QueryCache (in RAG pipeline) → ✅ Hit → Return
3. If miss: Run RAG Pipeline → Generate → Store in QueryCache → Return

#### `POST /api/v1/chat/stream`

**Changes**:
- **NEW**: Checks Suggested Question Cache FIRST (when chat_history is empty)
- **EXISTING**: Falls through to QueryCache → RAG pipeline if miss
- Streams cached response in chunks (simulated streaming)

**Response (Suggested Question Cache Hit)**:
```
data: {"status": "thinking", "chunk": "", "isComplete": false}

data: {"status": "streaming", "chunk": "Litecoin is a...", "isComplete": false}
...

data: {"status": "sources", "sources": [...], "isComplete": false}

data: {"status": "complete", "chunk": "", "isComplete": true, "fromCache": "suggested_question"}
```

---

## Testing

### Unit Tests

**SuggestedQuestionCache**:
- Test question normalization
- Test cache key generation (no chat history)
- Test Redis get/set operations
- Test error handling (Redis unavailable)
- Test TTL expiration

**Cache Layer Interaction**:
- Test Suggested Cache hit → return immediately
- Test Suggested Cache miss → QueryCache hit
- Test both miss → RAG pipeline
- Test independence of caches

### Integration Tests

**Multi-Layer Cache**:
- Test Suggested Cache → QueryCache → RAG flow
- Test cache independence (one can fail, other works)
- Test cache population on startup
- Test cache refresh

**End-to-End**:
- Test user clicking suggested question
- Test Suggested Cache hit (instant response)
- Test Suggested Cache miss → QueryCache hit
- Test both miss → RAG pipeline
- Test Redis unavailable scenario (QueryCache still works)

---

## Deployment

### Prerequisites

- Redis server running and accessible (same as rate limiting)
- Payload CMS accessible from backend
- `httpx` package installed

### Deployment Steps

1. **Update Dependencies**:
   ```bash
   # Ensure httpx is in requirements.txt
   pip install -r backend/requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   # Set PAYLOAD_URL in backend/.env
   PAYLOAD_URL=https://cms.lite.space
   ```

3. **Deploy Code**:
   ```bash
   # Deploy updated backend code
   # Restart backend service
   ```

4. **Verify Cache Population**:
   ```bash
   # Check application logs
   # Verify Suggested Question Cache refresh completed
   # Check Redis for cached entries
   redis-cli KEYS "suggested_question:*"
   ```

5. **Set Up Cron Job for Scheduled Refresh**:
   ```bash
   # Option 1: Using system cron (recommended for production)
   # Edit crontab: crontab -e
   # Add line to run every 2 days at 2:00 AM UTC:
   0 2 */2 * * /path/to/Litecoin-Knowledge-Hub/scripts/refresh-suggested-cache.sh >> /var/log/suggested-cache-refresh.log 2>&1
   
   # Option 2: Using Docker container cron (if running in container)
   # Add to Dockerfile or docker-compose.yml:
   # Install cron in container and configure
   
   # Option 3: Using application-level scheduler (APScheduler, Celery Beat, etc.)
   # Configure in main.py or separate scheduler service
   ```

   **Cron Job Configuration**:
   - **Schedule**: `0 2 */2 * *` (runs every 2 days at 2:00 AM UTC)
   - **Command**: HTTP POST to refresh endpoint or direct Python function call
   - **Logging**: Redirect output to log file for monitoring
   - **Error Handling**: Ensure failures are logged and alerting is configured
   - **Alternative Times**: Adjust based on traffic patterns (e.g., `0 3 * * *` for 3 AM)

6. **Monitor Performance**:
   ```bash
   # Check Suggested Question Cache hit rate
   # Check QueryCache hit rate (should remain similar)
   # Monitor overall response times
   # Verify cost reduction
   # Check cron job logs for refresh status
   tail -f /var/log/suggested-cache-refresh.log
   ```

7. **Verify Grafana Integration**:
   ```bash
   # Start monitoring stack (if not already running)
   docker-compose -f monitoring/docker-compose.monitoring.yml up -d
   
   # Verify metrics are being collected
   # Open Prometheus: http://localhost:9090
   # Query: suggested_question_cache_hits_total
   # Should show metric data if cache is being used
   
   # Access Grafana dashboard
   # Open: http://localhost:3002
   # Navigate to: Litecoin Knowledge Hub - Monitoring Dashboard
   # Verify Suggested Question Cache panels are displaying data
   ```

### Rollback Plan

If issues occur:
1. Feature can be disabled by removing Suggested Cache check in endpoints
2. System gracefully falls back to QueryCache → RAG pipeline
3. **No impact on existing QueryCache** (continues to work)
4. No data loss (cache is non-critical)

---

## Future Enhancements

### Phase 2: Cache Warming
- Populate Suggested Question Cache from QueryCache on startup
- Migrate popular QueryCache entries to Suggested Cache
- Learn from QueryCache which questions are frequently asked

### Phase 3: Incremental Refresh
- Only refresh questions that have changed
- Track question update timestamps
- Webhook integration for real-time updates

### Phase 4: Smart Caching
- Cache popular user questions (not just suggested)
- LRU eviction for non-suggested questions
- Cache warming based on usage patterns

### Phase 5: Cache Analytics
- Track which cached questions are most popular
- Compare Suggested Cache vs QueryCache hit rates
- A/B testing for cache TTL values
- Cost savings reporting
- Enhanced Grafana dashboards with per-question analytics
- Real-time cache performance alerts via Grafana
- Historical trend analysis for cache effectiveness

---

## Troubleshooting

### Common Issues

**Suggested Cache Not Populating**:
- Check Payload CMS connectivity
- Verify PAYLOAD_URL is correct
- Check application logs for errors
- Verify Redis is accessible
- **QueryCache continues to work normally**

**Suggested Cache Hits Not Working**:
- Verify question text matches exactly (check normalization)
- Check Redis keys exist: `redis-cli KEYS "suggested_question:*"`
- Verify cache TTL hasn't expired
- Check logs for cache lookup errors
- **QueryCache should still work as fallback**

**High Suggested Cache Miss Rate**:
- Verify questions in Payload match user queries
- Check question normalization logic
- Consider case-insensitive matching improvements
- **QueryCache should catch many of these**

**Redis Connection Errors**:
- Verify REDIS_URL is correct
- Check Redis server is running
- Verify network connectivity
- Check Redis authentication (if enabled)
- **QueryCache continues to work (in-memory)**

**Cron Job Not Running**:
- Verify cron job is installed and configured: `crontab -l`
- Check cron service is running: `systemctl status cron` (Linux) or `service cron status`
- Verify cron job log file exists and is writable: `ls -la /var/log/suggested-cache-refresh.log`
- Check cron job permissions and user context
- Test cron job manually: Run `./scripts/refresh-suggested-cache.sh` directly to verify it works
- Check system logs for cron errors: `grep CRON /var/log/syslog` (Linux)
- Verify timezone settings (cron uses system timezone)
- Verify `ADMIN_TOKEN` is accessible to cron (may need to source from `backend/.env` in the script)
- **Cache will still work but may expire if cron fails for >24 hours (TTL is 24h, refresh is every 48h)**

---

## Related Documentation

- [Environment Variables](./ENVIRONMENT_VARIABLES.md)
- [Redis Client Implementation](../backend/redis_client.py)
- [RAG Pipeline Documentation](../backend/rag_pipeline.py) - Contains QueryCache details
- [Payload CMS Integration](./milestones/milestone_5_payload_cms_setup_integration.md)
- [Monitoring Infrastructure](../monitoring/README.md) - Grafana and Prometheus setup
- [Monitoring Guide](./monitoring/monitoring-guide.md) - Comprehensive monitoring documentation
- [Grafana Dashboard](../monitoring/grafana/dashboards/litecoin-knowledge-hub.json) - Main monitoring dashboard

---

## Changelog

### 2025-01-XX - Initial Implementation
- Added SuggestedQuestionCache class (Redis-based, 24h TTL)
- Implemented cache refresh on startup
- Added scheduled refresh via cron job (runs every 24 hours)
- Updated chat endpoints to check Suggested Cache before QueryCache
- Added Payload CMS integration utility
- **Note**: Existing QueryCache (in-memory, 1h TTL) continues to work unchanged

---

## Implementation Notes

### Files Created
- `backend/utils/suggested_questions.py` - Payload CMS integration utility
- `backend/cache_utils.py` - Added `SuggestedQuestionCache` class

### Files Modified
- `backend/main.py` - Updated chat endpoints, added cache refresh function and admin endpoint
- `backend/monitoring/metrics.py` - Added Prometheus metrics for suggested question cache
- `backend/monitoring/__init__.py` - Exported new metrics
- `docs/setup/ENVIRONMENT_VARIABLES.md` - Documented new environment variables

### Key Implementation Details
- Cache uses Redis with 24-hour TTL (configurable via `SUGGESTED_QUESTION_CACHE_TTL`)
- Cache refresh runs automatically on application startup (non-blocking)
- Manual refresh available via `POST /api/v1/admin/refresh-suggested-cache` endpoint
- Admin endpoint requires Bearer token authentication (`ADMIN_TOKEN` environment variable)
- All cache operations are async and handle errors gracefully
- Metrics are tracked for cache hits, misses, lookup duration, cache size, and refresh operations

### Cron Job Setup (48-Hour Refresh)

For scheduled cache refresh every 48 hours (every 2 days), set up a cron job using the provided script:

#### Option 1: Using the Provided Script (Recommended)

```bash
# Edit crontab
crontab -e

# Add line to run every 2 days at 2:00 AM UTC
# This runs on the 1st, 3rd, 5th, etc. of each month
0 2 */2 * * /path/to/Litecoin-Knowledge-Hub/scripts/refresh-suggested-cache.sh >> /var/log/suggested-cache-refresh.log 2>&1
```

**Note:** The `*/2` pattern in the day-of-month field runs every 2 days, but it's not exactly 48 hours - it runs on odd-numbered days (1st, 3rd, 5th, etc.) at 2 AM.

#### Option 2: Using a Loop Script (True 48-Hour Interval)

For a true 48-hour interval, create a systemd service or use a loop script:

```bash
# Create a loop script that runs every 48 hours
cat > /usr/local/bin/refresh-cache-loop.sh << 'EOF'
#!/bin/bash
while true; do
    /path/to/Litecoin-Knowledge-Hub/scripts/refresh-suggested-cache.sh
    sleep 172800  # 48 hours in seconds (48 * 60 * 60)
done
EOF

chmod +x /usr/local/bin/refresh-cache-loop.sh

# Run as a systemd service or in a screen/tmux session
```

#### Option 3: Manual Cron with curl (Simple)

```bash
# Edit crontab
crontab -e

# Add line to run every 2 days at 2:00 AM UTC
0 2 */2 * * curl -X POST http://localhost:8000/api/v1/admin/refresh-suggested-cache -H "Authorization: Bearer $(grep ADMIN_TOKEN /path/to/backend/.env | cut -d '=' -f2)" >> /var/log/suggested-cache-refresh.log 2>&1
```

**Important:**
- Ensure `ADMIN_TOKEN` is set in `backend/.env` or exported in the cron environment
- Replace `localhost:8000` with your backend URL
- The script automatically loads `ADMIN_TOKEN` from `backend/.env` if available
- Logs are written to `/var/log/suggested-cache-refresh.log` by default (or `suggested-cache-refresh.log` in project root if log directory is not writable)

---

**Document Status**: ✅ Implemented

