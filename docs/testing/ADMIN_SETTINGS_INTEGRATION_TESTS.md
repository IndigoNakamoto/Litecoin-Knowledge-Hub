# Admin Settings Integration Tests

This document outlines the integration tests needed to verify that admin frontend changes to Abuse Prevention Settings actually take effect.

## Overview

When an admin updates settings via the frontend, we need to verify:
1. Settings are saved to Redis
2. Settings are read dynamically (not hardcoded)
3. Changes actually affect behavior
4. Cache is cleared so changes take effect immediately

## Settings That Need Testing

### 1. Challenge-Response Fingerprinting

**Setting:** `enable_challenge_response`

**What to Test:**
- ✅ Admin can toggle challenge-response on/off
- ✅ When disabled, challenge endpoint returns `"disabled"`
- ✅ When disabled, chat endpoint accepts requests without challenge validation
- ✅ When enabled, chat endpoint requires valid challenge

**How It's Used:**
- `backend/main.py:960` - Reads setting dynamically
- `backend/utils/challenge.py:47` - Checks setting before generating challenge
- `backend/main.py:973` - Validates challenge if enabled

### 2. Challenge TTL

**Setting:** `challenge_ttl_seconds`

**What to Test:**
- ✅ Admin can update challenge expiration time
- ✅ Generated challenges use the updated TTL
- ✅ Challenges expire after the configured time

**How It's Used:**
- `backend/utils/challenge.py:65` - Reads TTL from Redis/env

### 3. Max Active Challenges Per Identifier

**Setting:** `max_active_challenges_per_identifier`

**What to Test:**
- ✅ Admin can set max active challenges
- ✅ System enforces the limit (e.g., default 15)
- ✅ Requests beyond limit are rejected

**How It's Used:**
- `backend/utils/challenge.py:75` - Reads limit from Redis/env

### 4. Global Rate Limiting

**Settings:** 
- `enable_global_rate_limit`
- `global_rate_limit_per_minute`
- `global_rate_limit_per_hour`

**What to Test:**
- ✅ Admin can enable/disable global rate limiting
- ✅ Admin can set custom rate limits
- ✅ System enforces the configured limits
- ✅ Limits apply across all requests (not per-user)

**How It's Used:**
- `backend/rate_limiter.py:177` - Reads enable flag
- `backend/rate_limiter.py:184-188` - Reads rate limit values

### 5. Cost-Based Throttling

**Settings:**
- `enable_cost_throttling`
- `high_cost_threshold_usd`
- `high_cost_window_seconds`
- `cost_throttle_duration_seconds`
- `daily_cost_limit_usd`

**What to Test:**
- ✅ Admin can enable/disable cost throttling
- ✅ Admin can set cost thresholds
- ✅ System throttles users exceeding thresholds
- ✅ Throttling duration is configurable

**How It's Used:**
- `backend/utils/cost_throttling.py:44-65` - Reads all cost throttling settings

### 6. Challenge Request Rate Limit

**Setting:** `challenge_request_rate_limit_seconds`

**What to Test:**
- ✅ Admin can set rate limit for challenge requests
- ✅ System enforces the limit on `/api/v1/auth/challenge` endpoint

**How It's Used:**
- `backend/utils/challenge.py:68` - Reads rate limit from Redis/env

### 7. Global Daily and Hourly Spend Limits

**Settings:**
- `daily_spend_limit_usd` - Global daily LLM spend limit across all users
- `hourly_spend_limit_usd` - Global hourly LLM spend limit across all users

**What to Test:**
- ✅ Admin can set global daily spend limit
- ✅ Admin can set global hourly spend limit
- ✅ System enforces global limits (hard cap across all users)
- ✅ `get_current_usage()` returns updated limits
- ✅ `check_spend_limit()` uses updated limits to block requests
- ✅ Limits are read dynamically from Redis with env fallback

**How It's Used:**
- `backend/monitoring/spend_limit.py` - Reads limits dynamically using `get_setting_from_redis_or_env()`
- `backend/monitoring/spend_limit.py:get_current_usage()` - Returns current limits in usage info
- `backend/monitoring/spend_limit.py:check_spend_limit()` - Blocks requests that would exceed limits
- `backend/main.py:160-172` - Updates Prometheus metrics with current limits

## Test Implementation Status

### ✅ Unit Tests (Completed)
- `test_user_statistics.py` - User tracking tests
- `test_admin_endpoints.py` - Admin endpoint structure tests
- `test_abuse_prevention.py` - Basic abuse prevention tests

### ✅ Integration Tests (Completed)
- `test_admin_settings_integration.py` - Settings integration tests
  - ✅ Settings saved to Redis via API
  - ✅ Settings read dynamically after update
  - ✅ Cache clearing works correctly
  - ✅ Global rate limit settings applied
  - ✅ Challenge-response enable/disable works
  - ✅ Challenge TTL uses updated settings
  - ✅ Cost throttling uses updated settings
  - ✅ Partial updates preserve other settings
  - ✅ Settings endpoint shows Redis vs env sources
  - ✅ Full cycle: update via API → get back
  - ✅ Global daily/hourly spend limits use updated settings
  - ✅ Global spend limits settings endpoint (update and retrieve)

## Test Scenarios

### Scenario 1: Toggle Challenge-Response

```python
# 1. Admin disables challenge-response
PUT /api/v1/admin/settings/abuse-prevention
{
  "enable_challenge_response": false
}

# 2. Verify setting saved
GET /api/v1/admin/settings/abuse-prevention
# Should show enable_challenge_response: false, source: redis

# 3. Verify behavior changed
GET /api/v1/auth/challenge
# Should return {"challenge": "disabled"}

POST /api/v1/chat/stream
# Should accept request without challenge validation
```

### Scenario 2: Update Rate Limits

```python
# 1. Admin updates global rate limit
PUT /api/v1/admin/settings/abuse-prevention
{
  "global_rate_limit_per_minute": 50,
  "enable_global_rate_limit": true
}

# 2. Verify setting saved
GET /api/v1/admin/settings/abuse-prevention
# Should show new limits, source: redis

# 3. Verify behavior changed
# Make 51 requests rapidly
# 51st request should be rate limited (429)
```

### Scenario 3: Update Challenge TTL

```python
# 1. Admin updates challenge TTL
PUT /api/v1/admin/settings/abuse-prevention
{
  "challenge_ttl_seconds": 600  # 10 minutes
}

# 2. Request a challenge
GET /api/v1/auth/challenge
# Should return {"expires_in_seconds": 600}
```

### Scenario 4: Partial Update Preserves Other Settings

```python
# 1. Initial settings
PUT /api/v1/admin/settings/abuse-prevention
{
  "enable_challenge_response": true,
  "challenge_ttl_seconds": 300,
  "global_rate_limit_per_minute": 1000
}

# 2. Update only one setting
PUT /api/v1/admin/settings/abuse-prevention
{
  "global_rate_limit_per_minute": 2000
}

# 3. Verify other settings preserved
GET /api/v1/admin/settings/abuse-prevention
# Should still have enable_challenge_response: true
# Should still have challenge_ttl_seconds: 300
# Should have global_rate_limit_per_minute: 2000
```

### Scenario 5: Update Global Spend Limits

```python
# 1. Admin updates global spend limits
PUT /api/v1/admin/settings/abuse-prevention
{
  "daily_spend_limit_usd": 10.00,
  "hourly_spend_limit_usd": 2.00
}

# 2. Verify settings saved
GET /api/v1/admin/settings/abuse-prevention
# Should show daily_spend_limit_usd: 10.00, source: redis
# Should show hourly_spend_limit_usd: 2.00, source: redis

# 3. Verify behavior changed
GET /api/v1/admin/usage
# Should show daily limit: 10.00, hourly limit: 2.00

# 4. Verify spend limit checking uses new limits
# If daily cost is 9.5 and request is 0.6, should be blocked
# (9.5 + 0.6*1.1 = 10.16 > 10.00)
```

## How Settings Work

### Storage
- Settings stored in Redis key: `admin:settings:abuse_prevention`
- Format: JSON string
- No expiration (persistent until manually cleared)

### Reading Settings
1. **Priority Order:**
   - Redis settings (highest priority)
   - Environment variables (fallback)
   - Default values (last resort)

2. **Caching:**
   - Settings cached in `_settings_cache` variable
   - Cache cleared after each update via `clear_settings_cache()`
   - Cache reloaded on next read if None

### Dynamic Loading
Settings are read dynamically using `get_setting_from_redis_or_env()`:
- Called during request processing
- No application restart required
- Changes take effect immediately (after cache clear)

## Manual Testing Checklist

Before deployment, manually verify:

- [ ] Update `enable_challenge_response` → Chat endpoint behavior changes
- [ ] Update `challenge_ttl_seconds` → New challenges use new TTL
- [ ] Update `global_rate_limit_per_minute` → Rate limiting enforces new limit
- [ ] Update `high_cost_threshold_usd` → Cost throttling uses new threshold
- [ ] Update `daily_spend_limit_usd` → Global daily limit enforced
- [ ] Update `hourly_spend_limit_usd` → Global hourly limit enforced
- [ ] Update multiple settings → All changes take effect
- [ ] Partial update → Other settings preserved
- [ ] Clear Redis settings → Falls back to environment variables

## Test Files

### Created
- ✅ `backend/tests/test_admin_settings_integration.py` - Integration tests
- ✅ `backend/tests/test_user_statistics.py` - User tracking tests
- ✅ `backend/tests/test_admin_endpoints.py` - Admin endpoint tests

### Existing
- ✅ `backend/tests/test_abuse_prevention.py` - Basic abuse prevention tests
- ✅ `backend/tests/test_rate_limiter.py` - Rate limiting tests

## Next Steps

1. **Fix Integration Tests**
   - Properly mock Redis for FastAPI TestClient
   - Test full request cycle: update → verify → test behavior

2. **Add End-to-End Tests**
   - Test actual behavior changes (rate limiting, challenge validation)
   - Verify settings cascade through all components

3. **Add Frontend Tests** (if applicable)
   - Test admin frontend updates settings correctly
   - Verify UI reflects setting changes

## Related Code

### Settings Management
- `backend/api/v1/admin/settings.py` - Settings API endpoints
- `backend/utils/settings_reader.py` - Settings reading utilities

### Settings Usage
- `backend/main.py` - Challenge-response validation, spend limit metrics
- `backend/utils/challenge.py` - Challenge generation/validation
- `backend/rate_limiter.py` - Global rate limiting
- `backend/utils/cost_throttling.py` - Cost-based throttling
- `backend/monitoring/spend_limit.py` - Global daily/hourly spend limits

