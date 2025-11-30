# Testing Cost Throttling Atomic Optimization in Dev Mode

This guide explains how to test the atomic Lua script optimization for cost throttling in development mode.

## Prerequisites

1. **Start development services**:
   ```bash
   ./scripts/run-dev.sh
   ```

2. **Ensure Redis is running** (should be started by docker-compose.dev.yml)

3. **Enable cost throttling in dev mode** (it's disabled by default):
   - Option A: Via Admin Dashboard (recommended)
     - Access admin dashboard
     - Enable `enable_cost_throttling` setting
   - Option B: Via Environment Variable
     ```bash
     export ENABLE_COST_THROTTLING=true
     ```

4. **Disable challenge-response for testing** (optional, but recommended):
   - Challenge-response validation can block test requests
   - Option A: Via Admin Dashboard
     - Disable `enable_challenge_response` setting
   - Option B: Via Environment Variable
     ```bash
     export ENABLE_CHALLENGE_RESPONSE=false
     ```
   - **Note**: If challenge-response is enabled, you'll need to use valid challenges in fingerprints

## Testing Methods

### 1. Unit Tests (Recommended First Step)

Run the existing cost throttling tests:

```bash
cd backend
pytest tests/test_abuse_prevention.py::test_cost_throttling -v
pytest tests/test_admin_settings_integration.py::test_cost_throttling_uses_updated_settings -v
```

**Note**: These tests may need updates to mock `redis.eval()` instead of individual Redis operations. If tests fail, they need to be updated to work with Lua scripts.

### 2. Manual API Testing

#### Test Basic Cost Throttling

1. **Enable cost throttling** (see Prerequisites above)

2. **Send a request that should be allowed**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/stream \
     -H "Content-Type: application/json" \
     -H "X-Fingerprint: fp:test123:hash456" \
     -d '{
       "query": "What is Litecoin?",
       "chat_history": []
     }'
   ```

3. **Send multiple requests to trigger throttling**:
   ```bash
   # Send 10 requests rapidly with same fingerprint
   for i in {1..10}; do
     curl -X POST http://localhost:8000/api/v1/chat/stream \
       -H "Content-Type: application/json" \
       -H "X-Fingerprint: fp:test123:hash456" \
       -d "{\"query\": \"Test $i\", \"chat_history\": []}" \
       -w "\nStatus: %{http_code}\n" &
   done
   wait
   ```

   Expected: First few requests succeed, then you should see `429 Too Many Requests` with cost throttling message.

#### Test Concurrent Requests (Race Condition Fix)

This test verifies that the atomic optimization prevents race conditions:

```bash
# Send 10 concurrent requests with same fingerprint
# All should see the same cost state atomically
seq 1 10 | xargs -P 10 -I {} bash -c '
  curl -X POST http://localhost:8000/api/v1/chat/stream \
    -H "Content-Type: application/json" \
    -H "X-Fingerprint: fp:concurrent-test:hash789" \
    -d "{\"query\": \"Concurrent test {}\", \"chat_history\": []}" \
    -w "\nRequest {}: Status %{http_code}\n" \
    -s -o /dev/null
'
```

**Expected Behavior**:
- Only the first request(s) that fit within the limit should succeed
- Remaining requests should be throttled atomically (no race condition)
- All requests should see consistent cost state

#### Test Daily Limit

```bash
# Set a very low daily limit for testing
# (You'll need to set this in Redis or via admin dashboard)
# Then send requests that exceed it

curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-Fingerprint: fp:daily-test:hash999" \
  -d '{
    "query": "Test daily limit",
    "chat_history": []
  }'
```

### 3. Using Python Script for Testing

Create a test script `test_cost_throttling.py`:

```python
import asyncio
import aiohttp
import time

async def test_concurrent_requests():
    """Test concurrent requests to verify atomic behavior"""
    fingerprint = "fp:atomic-test:hash123"
    url = "http://localhost:8000/api/v1/chat/stream"
    
    headers = {
        "Content-Type": "application/json",
        "X-Fingerprint": fingerprint
    }
    
    async def send_request(i):
        data = {
            "query": f"Test request {i}",
            "chat_history": []
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data, headers=headers) as resp:
                    status = resp.status
                    text = await resp.text()
                    print(f"Request {i}: Status {status}")
                    if status == 429:
                        print(f"  Throttled: {text[:100]}")
                    return status
            except Exception as e:
                print(f"Request {i}: Error - {e}")
                return None
    
    # Send 10 concurrent requests
    print("Sending 10 concurrent requests...")
    tasks = [send_request(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r == 200)
    throttled_count = sum(1 for r in results if r == 429)
    
    print(f"\nResults: {success_count} succeeded, {throttled_count} throttled")
    print("If atomic optimization works, only requests within limit should succeed")

if __name__ == "__main__":
    asyncio.run(test_concurrent_requests())
```

Run it:
```bash
cd backend
python test_cost_throttling.py
```

### 4. Redis Inspection

Check Redis directly to verify the Lua scripts are working:

```bash
# Connect to Redis
docker exec -it litecoin-redis redis-cli

# Check throttle markers
KEYS llm:throttle:*

# Check cost tracking
KEYS llm:cost:recent:*
KEYS llm:cost:daily:*

# Inspect a specific cost key
ZRANGE llm:cost:recent:hash456 0 -1 WITHSCORES

# Check throttle marker TTL
TTL llm:throttle:hash456
```

### 5. Log Monitoring

Watch backend logs to see Lua script execution:

```bash
# In another terminal, watch backend logs
docker logs -f litecoin-backend | grep -i "cost\|throttle\|lua"
```

Look for:
- `"Cost throttling check called"` - Entry point
- `"Cost recorded for stable_identifier"` - Success
- `"Cost-based throttling triggered"` - Throttling
- `"Error executing cost throttle Lua script"` - Errors (should be rare)

## Expected Results

### Before Optimization (Old Behavior)
- Multiple concurrent requests could all pass the check
- Race conditions allowed bypassing limits
- 5+ Redis round-trips per request

### After Optimization (New Behavior)
- ✅ Atomic operations prevent race conditions
- ✅ Only requests within limits succeed
- ✅ Single Redis round-trip per request
- ✅ Consistent cost state across concurrent requests

## Verification Checklist

- [ ] Cost throttling can be enabled in dev mode
- [ ] Single requests below threshold are allowed
- [ ] Multiple requests exceeding threshold are throttled
- [ ] Concurrent requests see consistent state (no race condition)
- [ ] Daily limit enforcement works correctly
- [ ] Window limit enforcement works correctly
- [ ] Throttle markers are set with correct TTL
- [ ] Error handling works (fail-open strategy)
- [ ] Logs show Lua script execution
- [ ] Redis keys are created/updated correctly

## Troubleshooting

### Cost Throttling Not Working

1. **Check if it's enabled**:
   ```bash
   # Check environment
   echo $ENABLE_COST_THROTTLING
   
   # Check Redis settings
   docker exec -it litecoin-redis redis-cli GET settings
   ```

2. **Check dev mode detection**:
   ```bash
   # Should be "development" or DEBUG=true to disable by default
   echo $ENVIRONMENT
   echo $DEBUG
   ```

3. **Check backend logs**:
   ```bash
   docker logs litecoin-backend | grep -i "cost throttling"
   ```

### Lua Script Errors

If you see errors like "Error executing cost throttle Lua script":

1. **Check Redis connection**:
   ```bash
   docker exec -it litecoin-redis redis-cli PING
   ```

2. **Verify script syntax** (scripts are in `backend/utils/lua_scripts.py`)

3. **Check Redis version** (Lua scripts require Redis 2.6+)

### Tests Failing

If unit tests fail after the optimization:

1. Tests may need to mock `redis.eval()` instead of individual operations
2. Update test mocks to return expected Lua script response format: `[status_code, ttl_or_duration]`

## Performance Testing

To verify the performance improvement:

```bash
# Measure latency before (if you have old code) and after
time curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-Fingerprint: fp:perf-test:hash" \
  -d '{"query": "test", "chat_history": []}' \
  -w "\nTime: %{time_total}s\n"
```

Expected: ~75-80% latency reduction for cost throttling check (from ~5-10ms to ~1-2ms).

## Related Documentation

- [Cost Throttling Atomic Optimization](../fixes/COST_THROTTLING_ATOMIC_OPTIMIZATION.md)
- [Cost Throttling Enhancements](../fixes/COST_THROTTLING_ENHANCEMENTS.md)
- [Advanced Abuse Prevention Feature](../features/FEATURE_ADVANCED_ABUSE_PREVENTION.md)

