# Rate Limiter Atomic Optimization

**Date:** January 2025  
**Status:** 📋 Planned

---

## Executive Summary

Identified and documented a critical race condition vulnerability in the standard rate limiter's sliding window implementation. The current implementation uses 4 separate Redis operations that create a window where concurrent requests can bypass rate limits. This document outlines the fix: migrating to an atomic Lua script that consolidates all operations into a single transaction, bringing the rate limiter up to the same "fortress" standard as the cost throttler.

**Key Improvements:**
- **Atomicity**: All checks and updates happen in a single Redis transaction
- **Performance**: Reduced from 4 round-trips to 1 for `_get_sliding_window_count`
- **Race Condition Fix**: Concurrent requests can no longer bypass limits
- **Strict Enforcement**: If limit is 10/minute, request #11 will fail even if it arrives 0.0001ms after request #10
- **Deduplication Support**: Maintains existing deduplication logic for double-clicks

---

## Problem Identified

### The "Four-Step" Shuffle Vulnerability

The current `_get_sliding_window_count` function makes **4 separate network calls** to Redis for *every single check*:

1. `ZREMRANGEBYSCORE` (Clean old entries)
2. `ZADD` (Add current request)
3. `EXPIRE` (Keep key alive)
4. `ZCARD` (Count requests)

**The Race Condition:**

If 50 requests hit your API in the same millisecond:

1. They **ALL** clean the window (step 1)
2. They **ALL** add themselves to the ZSET (step 2)
3. They **ALL** count (step 4)

**Result:** If your limit is 10/minute, **all 50 will pass** because they all added themselves before any of them checked the count.

### Root Cause

**Current Implementation (`_get_sliding_window_count`):**
```python
# Step 1: Clean old entries
await redis.zremrangebyscore(key, 0, cutoff)

# Step 2: Add current request
await redis.zadd(key, {member_id: now})

# Step 3: Set TTL
await redis.expire(key, window_seconds + 60)

# Step 4: Count requests
count = await redis.zcard(key)
return count
```

**Total: 4 Redis round-trips per request**

**The Problem:**
- Multiple sequential Redis operations (clean → add → expire → count)
- No atomic transaction boundary
- Network latency between operations creates a window for race conditions
- Each operation sees a different state of the data

### Attack Scenario

**Example: Limit is 10 requests/minute**

1. **Request #1-10** arrive simultaneously
2. All 10 execute step 1 (clean): Window is empty
3. All 10 execute step 2 (add): All 10 add themselves → Count = 10
4. All 10 execute step 4 (count): All see count = 10 → All pass ✅
5. **Request #11-50** arrive 0.1ms later
6. All 40 execute step 1 (clean): Window still has 10 entries
7. All 40 execute step 2 (add): All 40 add themselves → Count = 50
8. All 40 execute step 4 (count): All see count = 50 → **All should fail, but...**
9. **Problem:** If requests #11-50 arrive before requests #1-10 finish step 4, they might all see count < 10 and pass

**Result:** 50 requests pass when only 10 should be allowed.

---

## Solution: Atomic Sliding Window Lua Script

### Architecture

Lua scripts run directly on the Redis server, allowing multiple operations to execute atomically in a single round-trip.

**Benefits:**
- **Atomicity**: All operations succeed or fail together
- **Performance**: Single network round-trip
- **Consistency**: No race conditions possible
- **Correctness**: Check and act happen atomically - physically unbreakable

### Implementation

#### 1. Lua Script: Atomic Sliding Window (`backend/utils/lua_scripts.py`)

Add this script alongside the existing `COST_THROTTLE_LUA`:

```lua
SLIDING_WINDOW_LUA = """
-- Atomic Sliding Window Rate Limit
-- Keys: [1] window_key
-- Args: [1] now (timestamp), [2] window_seconds, [3] limit, [4] member_id, [5] expire_seconds

local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_seconds = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member_id = ARGV[4]
local expire_seconds = tonumber(ARGV[5])

-- 1. Clean up old entries (atomic cleanup)
local cutoff = now - window_seconds
redis.call('ZREMRANGEBYSCORE', key, 0, cutoff)

-- 2. Count current active requests
local count = redis.call('ZCARD', key)

-- 3. Check logic
-- If we are already at or above limit, we need to check if THIS specific user 
-- is already in the set (deduplication/idempotency).
-- If they are, we update their timestamp (allow).
-- If they aren't, we reject.

local score = redis.call('ZSCORE', key, member_id)

if score then
    -- CASE A: User is already in the window (Duplicate request/Retrying)
    -- Update their timestamp to 'now' and allow
    redis.call('ZADD', key, now, member_id)
    redis.call('EXPIRE', key, expire_seconds)
    return {1, count} -- 1 = Allowed (Duplicate)
elseif count < limit then
    -- CASE B: Under limit, new request
    -- Add user
    redis.call('ZADD', key, now, member_id)
    redis.call('EXPIRE', key, expire_seconds)
    return {1, count + 1} -- 1 = Allowed (New)
else
    -- CASE C: Over limit, new request
    -- REJECT
    return {0, count} -- 0 = Rejected
end
"""
```

**Key Features:**
- **Atomic Operations**: Clean, count, check, and add happen in single transaction
- **Deduplication Support**: Checks if member already exists (handles double-clicks)
- **Strict Enforcement**: Count is checked BEFORE adding new member
- **Idempotent Updates**: Existing members update timestamp (deduplication)

#### 2. Refactored Python Function (`backend/rate_limiter.py`)

Replace `_get_sliding_window_count` with `_check_sliding_window`:

```python
from backend.utils.lua_scripts import SLIDING_WINDOW_LUA

async def _check_sliding_window(
    redis, key: str, window_seconds: int, limit: int, now: int, 
    deduplication_id: Optional[str] = None
) -> tuple[int, bool, int]:
    """
    Atomic check-and-update for sliding window.
    
    Returns:
        (count, allowed, retry_after)
        - count: Current count in window
        - allowed: True if request allowed, False if rejected
        - retry_after: Seconds to wait before retry (0 if allowed)
    """
    # Deduplication ID logic
    if deduplication_id:
        member_id = deduplication_id
    else:
        member_id = f"{now}:{uuid.uuid4().hex[:8]}"
    
    # Run the Atomic Script
    # Returns: [allowed (1/0), current_count]
    try:
        result = await redis.eval(
            SLIDING_WINDOW_LUA,
            1,  # numkeys
            key,
            now,
            window_seconds,
            limit,
            member_id,
            window_seconds + 60  # expire_seconds
        )
        
        allowed, count = result[0], result[1]
        
        if not allowed:
            # Calculate retry_after only if rejected to save CPU
            # Get the oldest timestamp in the window to calculate precise retry time
            oldest = await redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_ts = int(oldest[0][1])
                retry_after = max(1, window_seconds - (now - oldest_ts))
            else:
                retry_after = window_seconds  # Should not happen if count > 0
            
            return count, False, retry_after
        
        return count, True, 0
    
    except Exception as e:
        # Fail open fallback (log error in production)
        logger.error(f"Redis Lua Error in rate limiter: {e}")
        return 1, True, 0
```

#### 3. Update `check_rate_limit` Logic

Update the main function to use the atomic check:

```python
# ... inside check_rate_limit ...

# 4. Atomic Check (Replaces the old _get_sliding_window_count calls)

# Check Minute Window
min_count, min_allowed, min_retry = await _check_sliding_window(
    redis, minute_key, 60, config.requests_per_minute, now, full_fingerprint
)

if not min_allowed:
    # REJECT IMMEDIATELY - No need to check hour window if minute fails
    exceeded_minute = True
    retry_after = min_retry
else:
    # Only check hour if minute passed
    hour_count, hour_allowed, hour_retry = await _check_sliding_window(
        redis, hour_key, 3600, config.requests_per_hour, now, full_fingerprint
    )
    exceeded_hour = not hour_allowed
    retry_after = hour_retry

if exceeded_minute or exceeded_hour:
    # ... (Existing metric recording and Ban logic) ...
    
    detail = {
        "error": "rate_limited",
        "message": "Too many requests. Please slow down.",
        "retry_after_seconds": retry_after
    }
    raise HTTPException(...)
```

---

## Technical Details

### Lua Script: Sliding Window Rate Limit

**Script Location**: `backend/utils/lua_scripts.py::SLIDING_WINDOW_LUA`

**Keys:**
- `KEYS[1]`: `window_key` (Rate limit window ZSET)

**Arguments:**
- `ARGV[1]`: `now` (current timestamp)
- `ARGV[2]`: `window_seconds` (window duration in seconds)
- `ARGV[3]`: `limit` (maximum requests allowed in window)
- `ARGV[4]`: `member_id` (deduplication identifier, e.g., fingerprint)
- `ARGV[5]`: `expire_seconds` (key TTL in seconds)

**Return Codes:**
- `{1, count}`: Allowed - returns current count
  - First value `1` = allowed
  - Second value = current count in window
- `{0, count}`: Rejected - returns current count
  - First value `0` = rejected
  - Second value = current count in window

**Logic Flow:**
1. **Clean**: Remove entries older than `now - window_seconds`
2. **Count**: Get current count of active requests
3. **Check**: 
   - If member exists → Update timestamp (deduplication/idempotency) → Allow
   - If count < limit → Add member → Allow
   - If count >= limit → Reject
4. **Expire**: Set TTL to keep key alive

**Key Features:**
- **Atomic Check-and-Act**: Count is checked BEFORE adding new member
- **Deduplication Support**: Existing members update timestamp (handles double-clicks)
- **Strict Enforcement**: Impossible to bypass limits with concurrent requests
- **Efficient**: Single round-trip instead of 4

---

## Code Changes

### Updated File: `backend/utils/lua_scripts.py`

Add the new script:

```python
SLIDING_WINDOW_LUA = """
-- Atomic Sliding Window Rate Limit
-- [Full script implementation - see source code]
"""
```

### Updated File: `backend/rate_limiter.py`

**Before:**
```python
async def _get_sliding_window_count(
    redis, key: str, window_seconds: int, now: int, deduplication_id: Optional[str] = None
) -> int:
    # Remove entries outside the window
    cutoff = now - window_seconds
    await redis.zremrangebyscore(key, 0, cutoff)
    
    # Add current request
    if deduplication_id:
        member_id = deduplication_id
    else:
        member_id = f"{now}:{uuid.uuid4().hex[:8]}"
    
    await redis.zadd(key, {member_id: now})
    await redis.expire(key, window_seconds + 60)
    count = await redis.zcard(key)
    return count
```

**After:**
```python
async def _check_sliding_window(
    redis, key: str, window_seconds: int, limit: int, now: int, 
    deduplication_id: Optional[str] = None
) -> tuple[int, bool, int]:
    # Single atomic operation
    result = await redis.eval(
        SLIDING_WINDOW_LUA,
        1,  # Number of keys
        key,
        now,
        window_seconds,
        limit,
        member_id,
        window_seconds + 60
    )
    allowed, count = result[0], result[1]
    # Handle result...
```

---

## Performance Impact

### Latency Reduction

**Before:**
- `_get_sliding_window_count`: ~4-8ms (4 round-trips × 1-2ms each)

**After:**
- `_check_sliding_window`: ~1-2ms (1 round-trip)

**Improvement: 75% latency reduction**

### Throughput Improvement

- Reduced Redis connection pool pressure
- Lower network bandwidth usage
- Better scalability under high concurrent load
- Fewer Redis operations = lower CPU usage on Redis server

### Race Condition Elimination

**Before:**
- 50 concurrent requests could all pass the check
- All 50 add themselves before any check the count
- Result: 50 requests pass when limit is 10

**After:**
- Only the first 10 requests pass
- Remaining 40 requests see updated count and are rejected
- Result: Exactly 10 requests pass (strict enforcement)

---

## Security Improvements

### 1. Atomic Limit Enforcement

**Before:** Limits could be bypassed by concurrent requests  
**After:** Limits are enforced atomically - impossible to bypass

### 2. Strict Enforcement

**Before:** Request #11 could pass if it arrived before request #10 finished counting  
**After:** Request #11 will fail even if it arrives 0.0001ms after request #10

### 3. Consistent State

**Before:** Clean, add, and count operations could see different states  
**After:** All operations see the same atomic state

### 4. Fortress-Grade Security

**Before:** Rate limiter was the "weak link" compared to cost throttler  
**After:** Rate limiter matches cost throttler's atomic "fortress" standard

---

## Error Handling

### Fail-Open Strategy

If the Lua script execution fails (Redis error, script error, etc.), the system:
1. Logs the error with full context
2. Allows the request to proceed (fail-open)
3. Prevents blocking legitimate users during infrastructure issues

**Rationale:**
- Rate limiting is a protection mechanism, not a critical path
- Better to allow a request than block legitimate users
- Errors are logged for investigation

### Error Logging

All errors include:
- Exception details with stack trace
- Fingerprint (truncated for privacy)
- Redis key (truncated)
- Window configuration (seconds, limit)

---

## Testing Recommendations

### 1. Concurrent Request Test

**Test Scenario:**
- Send 50 concurrent requests with the same fingerprint
- Rate limit: 10 requests/minute

**Expected Result:**
- First 10 requests: Allowed
- Remaining 40 requests: Rejected with 429 status

**Verification:**
```bash
# Use Apache Bench or similar
ab -n 50 -c 50 -H "X-Fingerprint: fp:challenge123:hash456" \
   http://localhost:8000/api/v1/chat
```

### 2. Deduplication Test

**Test Scenario:**
- Send 2 requests with the same fingerprint (double-click)
- Rate limit: 10 requests/minute

**Expected Result:**
- Both requests: Allowed (deduplication)
- Count: 1 (not 2)

### 3. Edge Case: Limit Boundary

**Test Scenario:**
- Send exactly 10 requests (at the limit)
- Send 11th request immediately after

**Expected Result:**
- First 10 requests: Allowed
- 11th request: Rejected (strict enforcement)

### 4. Performance Test

**Test Scenario:**
- Measure latency before and after optimization
- Test under high concurrent load (100+ requests/second)
- Verify no degradation under load

**Expected Result:**
- 75% latency reduction
- No performance degradation under load
- Consistent behavior under high concurrency

### 5. Race Condition Stress Test

**Test Scenario:**
- Send 100 requests simultaneously (all arrive within 1ms)
- Rate limit: 10 requests/minute

**Expected Result:**
- Exactly 10 requests pass
- Remaining 90 requests rejected
- No race condition bypass

---

## Configuration

No configuration changes required. The optimization is transparent to existing settings:

- `requests_per_minute`: Still configurable via `RateLimitConfig`
- `requests_per_hour`: Still configurable via `RateLimitConfig`
- `enable_progressive_limits`: Still works as before
- `progressive_ban_durations`: Still works as before

---

## Migration Notes

### Backward Compatibility

✅ **Fully backward compatible**
- All existing settings continue to work
- No API changes
- No database schema changes
- No frontend changes required
- Deduplication logic preserved

### Deployment

**Zero-downtime deployment:**
1. Deploy new code with Lua script
2. New requests automatically use optimized path
3. Old Redis data remains compatible
4. No migration scripts needed

### Rollback Plan

If issues arise:
1. Revert to previous version of `rate_limiter.py`
2. Remove `SLIDING_WINDOW_LUA` from `lua_scripts.py` (not used by old code)
3. System returns to previous behavior

---

## Monitoring

### Key Metrics to Monitor

1. **Lua Script Execution Time**
   - Should be < 5ms (p99)
   - Alert if > 10ms

2. **Lua Script Error Rate**
   - Should be < 0.1%
   - Alert if > 1%

3. **Rate Limiting Latency**
   - Should be < 2ms (p99)
   - Compare with pre-optimization baseline

4. **Rate Limit Rejection Rate**
   - Monitor for unexpected spikes
   - Should remain consistent with pre-optimization (or decrease due to stricter enforcement)

### Logging

All Lua script executions are logged:
- Success: INFO level with count details
- Rejection: WARNING level with retry_after
- Error: ERROR level with full context

---

## Related Documentation

- [Cost Throttling Atomic Optimization](./COST_THROTTLING_ATOMIC_OPTIMIZATION.md) - Similar atomic optimization for cost throttling
- [Rate Limiter Deduplication Fix](./RATE_LIMITER_DEDUPLICATION_FIX.md) - Related deduplication improvements
- [Advanced Abuse Prevention Feature](../features/FEATURE_ADVANCED_ABUSE_PREVENTION.md) - Overall abuse prevention system

---

## Future Enhancements

### Script Caching (EVALSHA)

For high-throughput scenarios, consider using `EVALSHA` instead of `EVAL`:

**Benefits:**
- Scripts cached on Redis server
- Slightly faster execution
- Reduced network bandwidth

**Implementation:**
```python
# Load script once
script_sha = await redis.script_load(SLIDING_WINDOW_LUA)

# Use cached script
result = await redis.evalsha(script_sha, 1, ...)
```

**Trade-off:**
- Slightly more complex error handling (NOSCRIPT errors)
- Minimal performance gain for most use cases
- Standard `EVAL` is sufficient for current scale

### Additional Optimizations

1. **Batch Rate Limit Checks**: Check multiple windows in single script call
2. **Precise Retry-After**: Calculate retry_after inside Lua script (eliminate extra ZRANGE call)
3. **Sliding Window Optimization**: Use Redis streams instead of sorted sets for very high throughput

---

## Comparison: Before vs After

### Before (Vulnerable)

```
Request #1-50 arrive simultaneously
├─ All 50: ZREMRANGEBYSCORE (clean)
├─ All 50: ZADD (add themselves)
├─ All 50: EXPIRE (set TTL)
└─ All 50: ZCARD (count) → All see count < 10 → All pass ❌
```

**Result:** 50 requests pass when limit is 10

### After (Atomic)

```
Request #1-50 arrive simultaneously
└─ All 50: EVAL (atomic script)
   ├─ Request #1-10: Count < 10 → Add → Allow ✅
   └─ Request #11-50: Count >= 10 → Reject ❌
```

**Result:** Exactly 10 requests pass (strict enforcement)

---

## Conclusion

The atomic Lua script optimization provides:
- ✅ **Race condition elimination** - No more concurrent bypass
- ✅ **75% latency reduction** - Single round-trip instead of 4
- ✅ **Strict enforcement** - Physically unbreakable limits
- ✅ **Improved scalability** - Better performance under high load
- ✅ **Fortress-grade security** - Matches cost throttler's atomic standard
- ✅ **Zero breaking changes** - Fully backward compatible
- ✅ **Deduplication preserved** - Double-clicks still handled correctly

This optimization brings the standard rate limiter up to the same "Fortress" standard as the cost throttler, eliminating the race condition vulnerability and ensuring strict limit enforcement regardless of concurrency.

---

**Document Created**: January 2025  
**Status**: 📋 Planned  
**Related Files**:
- `backend/utils/lua_scripts.py` (add `SLIDING_WINDOW_LUA`)
- `backend/rate_limiter.py` (replace `_get_sliding_window_count` with `_check_sliding_window`)

