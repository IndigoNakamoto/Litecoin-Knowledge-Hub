# Abuse Prevention Stack

This document provides a comprehensive overview of the multi-layered abuse prevention system implemented in the Litecoin Knowledge Hub API. The system combines rate limiting, challenge-response fingerprinting, bot protection, input sanitization, cost throttling, and webhook authentication to prevent various forms of abuse.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Rate Limiting](#rate-limiting)
3. [Challenge-Response Fingerprinting](#challenge-response-fingerprinting)
4. [Bot Protection (Cloudflare Turnstile)](#bot-protection-cloudflare-turnstile)
5. [Input Sanitization](#input-sanitization)
6. [Cost-Based Throttling](#cost-based-throttling)
7. [Webhook Authentication](#webhook-authentication)
8. [Atomic Operations (Lua Scripts)](#atomic-operations-lua-scripts)
9. [Integration Flow](#integration-flow)
10. [Configuration](#configuration)
11. [Monitoring & Metrics](#monitoring--metrics)

---

## Architecture Overview

The abuse prevention stack operates in multiple layers, each addressing different attack vectors:

```
┌─────────────────────────────────────────────────────────────┐
│                    Request Flow                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Input Sanitization                                       │
│     - Prompt injection detection                             │
│     - NoSQL injection prevention                            │
│     - Length validation                                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Challenge-Response Fingerprinting                        │
│     - Challenge generation & validation                      │
│     - Replay attack prevention                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Bot Protection (Turnstile)                               │
│     - CAPTCHA alternative                                    │
│     - Graceful degradation                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Rate Limiting                                            │
│     - Per-user sliding window                                │
│     - Global rate limits                                     │
│     - Progressive bans                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Cost-Based Throttling                                    │
│     - Spending window limits                                 │
│     - Daily cost caps                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Request Processing                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Rate Limiting

### Overview

The rate limiting system uses Redis-based sliding window algorithms to track and limit requests per user. It supports both per-user and global rate limits with progressive bans for repeated violations.

### Features

#### 1. **Sliding Window Rate Limiting**

- **Algorithm**: Redis sorted sets with atomic Lua scripts
- **Windows**: Per-minute and per-hour limits
- **Deduplication**: Prevents double-counting duplicate requests (idempotency)
- **Atomic Operations**: All checks and updates happen in a single Redis transaction

#### 2. **Stable Identifier Extraction**

The system extracts stable identifiers from fingerprints to ensure rate limits apply consistently:

- **Fingerprint Format**: `fp:challenge:hash`
- **Stable Identifier**: Extracts the `hash` part (last segment after colons)
- **Fallback**: Uses IP address if no fingerprint provided
- **IPv6 Support**: Handles IPv6 addresses correctly (doesn't break on colons)

#### 3. **Progressive Bans**

Repeated violations trigger escalating ban durations:

- **1st Violation**: 1 minute ban
- **2nd Violation**: 5 minutes ban
- **3rd Violation**: 15 minutes ban
- **4th Violation**: 60 minutes ban

Bans are tracked by IP address to prevent evasion via new challenges.

#### 4. **Global Rate Limits**

System-wide limits prevent aggregate abuse:

- **Per-Minute**: Default 1000 requests/minute (configurable)
- **Per-Hour**: Default 50,000 requests/hour (configurable)
- **Admin Exemption**: Admin endpoints bypass global limits
- **Dynamic Configuration**: Limits can be adjusted via Redis settings

#### 5. **IP Extraction Security**

Hardened IP extraction prevents spoofing attacks:

**Priority Order:**
1. `CF-Connecting-IP` (Cloudflare) - Always trusted
2. `X-Forwarded-For` - Only trusted when `TRUST_X_FORWARDED_FOR=true`
3. `request.client.host` - Direct connection fallback

**Security Features:**
- IP validation (IPv4/IPv6)
- Header spoofing prevention
- Configurable trust model

### Configuration

```python
# Per-endpoint rate limits
STREAM_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=60,
    requests_per_hour=1000,
    identifier="chat_stream",
    enable_progressive_limits=True,
)

# Challenge endpoint (stricter)
CHALLENGE_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=10,  # 1000 in dev
    requests_per_hour=100,   # 10000 in dev
    identifier="challenge",
    enable_progressive_limits=True,
)
```

### Response Format

When rate limited, the API returns:

```json
{
  "error": "rate_limited",
  "message": "Too many requests. You have been temporarily banned.",
  "limits": {
    "per_minute": 60,
    "per_hour": 1000
  },
  "violation_count": 2,
  "ban_expires_at": 1735689600,
  "retry_after_seconds": 300
}
```

**Headers:**
- `Retry-After: <seconds>` - Time to wait before retry

---

## Challenge-Response Fingerprinting

### Overview

Challenge-response fingerprinting prevents fingerprint replay attacks by requiring clients to include a server-generated, one-time-use challenge in their fingerprint. The system combines client-side browser fingerprinting with server-side challenge validation to create a robust user identification system.

### Client-Side Fingerprinting

#### Browser Fingerprint Generation

The client generates a stable browser fingerprint using persistent browser characteristics:

**Characteristics Used:**
- User agent, language, platform, vendor
- Screen resolution (width/height - stable, not window size)
- Color depth, pixel depth, device pixel ratio
- Timezone offset
- Hardware concurrency, device memory
- Touch support, cookie/storage support
- Session ID (unique per browser session)

**Implementation Details:**
- **Hash Algorithm**: SHA-256 via Web Crypto API (fallback available)
- **Hash Length**: 32 hex characters (128 bits)
- **Persistence**: Stored in `localStorage` to ensure consistency across page loads
- **Session ID**: Stored in `sessionStorage` (works in incognito mode)
- **Exclusions**: Window dimensions excluded (change with resizing)

**Benefits:**
- Prevents multiple "unique users" from the same browser
- Stable across page reloads (via localStorage)
- Works in incognito mode (session ID persists during session)
- Low collision probability (128-bit hash)

#### Fingerprint Format

**Base Fingerprint**: 32-character hex hash
```
hash4567890abcdef1234567890abcdef
```

**Challenge-Response Format**: `fp:challenge:hash`
```
fp:challenge123:hash4567890abcdef1234567890abcdef
```

**Format Components:**
- `fp:` - Prefix indicating fingerprint format
- `challenge` - Server-generated challenge ID (64 hex chars)
- `hash` - Base browser fingerprint hash (32 hex chars)

### How It Works

1. **Client generates base fingerprint** → Computes hash from browser characteristics
2. **Client requests challenge** → Sends base fingerprint to `/api/v1/auth/challenge`
3. **Server generates challenge** → Creates unique challenge ID, stores with identifier
4. **Client computes challenge fingerprint** → Combines challenge with base hash: `fp:challenge:hash`
5. **Client sends request** → Includes challenge fingerprint in `X-Fingerprint` header
6. **Server validates** → Verifies challenge exists and was issued to correct identifier
7. **Server consumes challenge** → Challenge deleted (one-time use)

### Features

#### 1. **Challenge Generation**

- **Unique IDs**: 64-character hex tokens (32 bytes)
- **TTL**: Configurable expiration (default: 300 seconds)
- **Rate Limited**: Prevents challenge exhaustion attacks
- **Active Challenge Limits**: Max 15 active challenges per identifier (100 in dev)

#### 2. **Smart Reuse (Idempotency)**

If a user requests a challenge too quickly (within rate limit window), the system:
- Checks for a recently generated challenge
- Returns the existing challenge instead of erroring
- Prevents 429 errors during rapid page loads

#### 3. **Progressive Bans**

Similar to rate limiting, challenge generation violations trigger bans:
- **1st Violation**: 1 minute ban
- **2nd Violation**: 5 minutes ban

#### 4. **Identifier Tracking**

Challenges are tied to identifiers (fingerprint hash or IP) to prevent:
- Challenge sharing between users
- Replay attacks with stolen challenges

#### 5. **Stable Identifier Extraction**

The system extracts stable identifiers from fingerprints for rate limiting and cost tracking:

**Extraction Logic:**
- **Format**: `fp:challenge:hash`
- **Stable Identifier**: Extracts the `hash` part (last segment after colons)
- **Purpose**: Ensures rate limits apply to user, not challenge session
- **IPv6 Safe**: Only splits if starts with `fp:`, so IPv6 addresses pass through unchanged

**Example:**
```python
fingerprint = "fp:challenge123:hash456"
stable_identifier = "hash456"  # Used for rate limit bucket
full_fingerprint = "fp:challenge123:hash456"  # Used for deduplication
```

**Benefits:** 
- Prevents bypass via new challenges (same user = same bucket)
- Allows retries (same challenge = deduplicated)
- Different challenges count separately (but same bucket)

### Configuration

```python
# Settings (Redis/env)
enable_challenge_response = True  # Enable/disable feature
challenge_ttl_seconds = 300        # Challenge expiration
challenge_request_rate_limit_seconds = 3  # Min time between requests
max_active_challenges_per_identifier = 15  # Max concurrent challenges
```

### Integration with Rate Limiting

Fingerprints are used in a two-part identifier strategy:

1. **Stable Identifier (Bucket Key)**: Extracted hash from fingerprint
   - Used for: Redis key (`rl:chat_stream:{stable_identifier}:m`)
   - Purpose: Rate limits apply to user, not challenge session
   - Example: `hash456` from `fp:challenge123:hash456`

2. **Full Fingerprint (Deduplication ID)**: Complete fingerprint string
   - Used for: Redis sorted set member (deduplication)
   - Purpose: Prevents double-counting same request
   - Example: `fp:challenge123:hash456`

**Benefits:**
- ✅ Same user gets same rate limit bucket across challenges
- ✅ Same challenge + same request = counted once (idempotency)
- ✅ Different challenges = new request (but same bucket)

### Integration with Cost Throttling

Cost throttling uses the same stable identifier extraction:
- Costs tracked by stable identifier (fingerprint hash)
- Prevents bypassing limits by getting new challenges
- Full fingerprint used for request deduplication

### API Endpoint

```
GET /api/v1/auth/challenge
```

**Request Headers:**
- `X-Fingerprint` (optional): Base fingerprint hash for identifier tracking

**Response:**
```json
{
  "challenge": "abc123...",
  "expires_in_seconds": 300
}
```

### Security Considerations

**Strengths:**
- ✅ Challenge-response prevents replay attacks
- ✅ Stable identifier prevents bypass via new challenges
- ✅ One-time challenges prevent reuse
- ✅ localStorage persistence prevents multiple "users" from same browser
- ✅ IPv6 addresses handled correctly

**Limitations:**
- ⚠️ Clearing localStorage resets fingerprint (rate limits reset)
- ⚠️ Session ID resets on browser close in incognito (expected behavior)
- ⚠️ Client-side generation means users could modify fingerprint (mitigated by challenge-response)

**Mitigations:**
- Progressive bans track by IP (prevents evasion)
- Challenge validation ensures fingerprints are legitimate
- Rate limits still apply even with modified fingerprints

---

## Bot Protection (Cloudflare Turnstile)

### Overview

Cloudflare Turnstile provides invisible bot protection without traditional CAPTCHA puzzles. The system implements graceful degradation - if Turnstile fails, stricter rate limits are applied instead of blocking requests.

### Features

#### 1. **Invisible Verification**

- No user interaction required
- Privacy-focused (no tracking)
- Fast verification (< 1 second)

#### 2. **Graceful Degradation**

If Turnstile verification fails:
- **Not blocked** - Request continues
- **Stricter rate limits applied** - 10x stricter (6/min, 60/hour)
- **Logging** - Failed verifications are logged for monitoring

#### 3. **Error Handling**

The system handles various failure modes:
- **Missing token**: Falls back to strict rate limits
- **API timeout**: Falls back to strict rate limits
- **Network errors**: Falls back to strict rate limits
- **Invalid token**: Falls back to strict rate limits

**Never returns 5xx errors** - Always fails open to prevent blocking legitimate users.

### Configuration

```bash
# Environment variables
ENABLE_TURNSTILE=true
TURNSTILE_SECRET_KEY=your-secret-key
```

### Integration

Turnstile verification happens after challenge validation but before rate limiting:

```python
# In chat endpoint
if is_turnstile_enabled():
    turnstile_result = await verify_turnstile_token(token, client_ip)
    if not turnstile_result.get("success"):
        # Apply stricter rate limits (10x)
        await check_rate_limit(request, STRICT_RATE_LIMIT)
        # Continue processing (don't block)
```

---

## Input Sanitization

### Overview

Input sanitization prevents injection attacks and enforces length limits on user inputs.

### Features

#### 1. **Prompt Injection Detection**

Detects and neutralizes prompt injection attempts:

**Detected Patterns:**
- `ignore previous instructions`
- `forget everything`
- `new instructions`
- `system:`
- `you are now`
- `act as if`
- `jailbreak`
- `roleplay`
- And more...

**Neutralization:**
- Wraps suspicious phrases: `[user input: <phrase>]`
- Preserves text but prevents interpretation as instructions

#### 2. **NoSQL Injection Prevention**

Prevents MongoDB injection attacks:

**Escaped Characters:**
- Null bytes (`\x00`)
- MongoDB operators (`$where`, `$ne`, `$gt`, etc.)
- Dollar signs followed by letters

**Query Parameter Sanitization:**
- Strips non-alphanumeric characters (except spaces, hyphens, underscores)
- Strict sanitization for direct query use

#### 3. **Length Validation**

- **Max Query Length**: 400 characters (configurable)
- **Truncation**: Inputs exceeding limit are truncated
- **Validation**: Returns error if length exceeds limit

#### 4. **Control Character Removal**

Removes dangerous control characters:
- Null bytes
- Control characters (except newlines, tabs, carriage returns)

### Usage

```python
from backend.utils.input_sanitizer import sanitize_query_input

# Comprehensive sanitization
sanitized = sanitize_query_input(user_input)

# Individual checks
is_injection, pattern = detect_prompt_injection(text)
sanitized = sanitize_prompt_injection(text)
sanitized = sanitize_nosql_injection(text)
```

---

## Cost-Based Throttling

### Overview

Cost-based throttling prevents abuse by tracking spending per user in sliding windows. Users exceeding spending thresholds are throttled to prevent excessive API costs.

### Features

#### 1. **Sliding Window Tracking**

- **Window Duration**: Configurable (default: 600 seconds / 10 minutes)
- **Threshold**: Configurable (default: $0.02 USD)
- **Daily Limit**: Hard cap per day (default: $0.25 USD)

#### 2. **Stable Identifier Tracking**

Costs are tracked by stable identifier (fingerprint hash) to prevent:
- Bypassing limits by getting new challenges
- Cost accumulation across different challenge sessions

#### 3. **Deduplication**

Uses full fingerprint (including challenge) for deduplication:
- Same challenge + same cost = counted once
- Different challenges = counted separately (but same stable identifier)

#### 4. **Throttle Duration**

When threshold exceeded:
- **Window Threshold**: 30 seconds throttle (configurable)
- **Daily Limit**: 2x throttle duration (60 seconds)

#### 5. **Development Mode**

- **Disabled by default** in development
- **Can be enabled** via admin dashboard or environment variable
- **Admin override** takes precedence over dev mode

### Configuration

```python
# Settings (Redis/env)
enable_cost_throttling = True  # Enable/disable
high_cost_threshold_usd = 0.02  # Window threshold
high_cost_window_seconds = 600  # Window duration
cost_throttle_duration_seconds = 30  # Throttle duration
daily_cost_limit_usd = 0.25  # Daily hard cap
```

### Response Format

When throttled:

```json
{
  "error": "cost_throttled",
  "message": "High usage detected. Please complete security verification and try again in 30 seconds.",
  "requires_verification": true
}
```

---

## Webhook Authentication

### Overview

Webhook authentication verifies requests from Payload CMS using HMAC-SHA256 signatures and timestamp validation to prevent replay attacks.

### Features

#### 1. **HMAC Signature Verification**

- **Algorithm**: HMAC-SHA256
- **Secret**: Shared secret from `WEBHOOK_SECRET` environment variable
- **Constant-Time Comparison**: Prevents timing attacks

#### 2. **Timestamp Validation**

- **Tolerance**: 5 minutes (300 seconds)
- **Prevents**: Replay attacks with old requests
- **Validates**: Request freshness

#### 3. **Header Requirements**

Required headers:
- `X-Webhook-Signature`: HMAC signature
- `X-Webhook-Timestamp`: Unix timestamp

### Usage

```python
from backend.utils.webhook_auth import verify_webhook_request

# In webhook endpoint
is_valid, error = await verify_webhook_request(request, body_bytes)
if not is_valid:
    raise HTTPException(status_code=401, detail=error)
```

---

## Atomic Operations (Lua Scripts)

### Overview

Redis Lua scripts ensure atomic operations for rate limiting and cost throttling, eliminating race conditions where concurrent requests could bypass limits.

### Scripts

#### 1. **SLIDING_WINDOW_LUA**

Atomic sliding window rate limit check:

**Operations:**
1. Clean expired entries
2. Count current requests
3. Check if limit exceeded
4. Add new request (if allowed)
5. Return result

**Returns:**
- `[allowed (1/0), count, oldest_timestamp]`

**Deduplication:**
- If member exists: Update timestamp, allow (idempotent)
- If under limit: Add new member, allow
- If over limit: Reject, return oldest timestamp for retry calculation

#### 2. **COST_THROTTLE_LUA**

Atomic cost throttling check:

**Operations:**
1. Check if already throttled
2. Clean expired entries from window
3. Calculate total cost in window
4. Calculate total daily cost
5. Check daily limit (hard cap)
6. Check window threshold
7. Record cost (if allowed)

**Returns:**
- `[status_code, ttl_or_duration]`
  - `0`: Allowed
  - `1`: Already throttled (returns remaining TTL)
  - `2`: Daily limit exceeded (returns throttle duration)
  - `3`: Window threshold exceeded (returns throttle duration)

#### 3. **RECORD_COST_LUA**

Atomic cost recording (after LLM call completes):

**Operations:**
1. Record in window ZSET
2. Record in daily ZSET
3. Set TTLs

**Use Case:**
- Updates cost tracking with actual cost (replaces estimated cost)

### Benefits

- **Atomicity**: All operations in single Redis transaction
- **Race Condition Prevention**: Concurrent requests can't bypass limits
- **Performance**: Single round-trip to Redis
- **Consistency**: Guaranteed accurate counts

---

## Integration Flow

### Chat Endpoint Flow

```
1. Request arrives
   ↓
2. Input Sanitization
   - Detect prompt injection
   - Sanitize NoSQL injection
   - Validate length
   ↓
3. Challenge Validation
   - Extract challenge from fingerprint
   - Validate challenge exists
   - Verify challenge issued to correct identifier
   - Consume challenge (one-time use)
   ↓
4. Turnstile Verification (if enabled)
   - Verify token with Cloudflare
   - On failure: Apply strict rate limits (don't block)
   ↓
5. Rate Limiting
   - Extract stable identifier
   - Check progressive bans
   - Check global rate limits
   - Check per-user rate limits (atomic)
   ↓
6. Cost-Based Throttling
   - Estimate cost
   - Check spending window
   - Check daily limit
   - Record estimated cost (atomic)
   ↓
7. Process Request
   - RAG pipeline
   - LLM call
   - Record actual cost
   ↓
8. Return Response
```

### Challenge Endpoint Flow

```
1. Request arrives
   ↓
2. Rate Limiting (challenge-specific limits)
   - Extract identifier (stable hash or IP)
   - Check progressive bans
   ↓
3. Challenge Generation
   - Check active challenge count
   - Check rate limit (time since last request)
   - Generate unique challenge ID
   - Store in Redis with TTL
   ↓
4. Return Challenge
```

---

## Configuration

### Environment Variables

```bash
# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
ENABLE_GLOBAL_RATE_LIMIT=true
GLOBAL_RATE_LIMIT_PER_MINUTE=1000
GLOBAL_RATE_LIMIT_PER_HOUR=50000
TRUST_X_FORWARDED_FOR=false  # Only true behind trusted proxy

# Challenge-Response
ENABLE_CHALLENGE_RESPONSE=true
CHALLENGE_TTL_SECONDS=300
CHALLENGE_REQUEST_RATE_LIMIT_SECONDS=3
MAX_ACTIVE_CHALLENGES_PER_IDENTIFIER=15

# Turnstile
ENABLE_TURNSTILE=true
TURNSTILE_SECRET_KEY=your-secret-key

# Cost Throttling
ENABLE_COST_THROTTLING=true
HIGH_COST_THRESHOLD_USD=0.02
HIGH_COST_WINDOW_SECONDS=600
COST_THROTTLE_DURATION_SECONDS=30
DAILY_COST_LIMIT_USD=0.25

# Webhook Auth
WEBHOOK_SECRET=your-webhook-secret
```

### Redis Settings (Admin Dashboard)

All settings can be dynamically updated via Redis (admin dashboard):

- `enable_global_rate_limit`
- `global_rate_limit_per_minute`
- `global_rate_limit_per_hour`
- `enable_challenge_response`
- `challenge_ttl_seconds`
- `enable_cost_throttling`
- `high_cost_threshold_usd`
- `daily_cost_limit_usd`
- And more...

**Settings are read with environment variable fallbacks** - Redis takes precedence.

---

## Monitoring & Metrics

### Prometheus Metrics

#### Rate Limiting
- `rate_limit_rejections_total` - Total rejections by endpoint
- `rate_limit_bans_total` - Total bans applied
- `rate_limit_violations_total` - Total violations
- `rate_limit_retry_after_seconds` - Retry-after times (histogram)
- `rate_limit_checks_total` - Total checks (allowed/rejected)

#### Challenge-Response
- `challenge_generation_total` - Challenge generations (success/rate_limited/banned)
- `challenge_validations_total` - Challenge validations (success/failure)
- `challenge_validation_failures_total` - Validation failures by reason
- `challenge_reuse_attempts_total` - Replay attack attempts

#### Cost Throttling
- `cost_throttle_triggers_total` - Throttle triggers by reason
- `cost_throttle_active_users` - Currently throttled users (gauge)
- `cost_recorded_usd_total` - Total cost recorded (estimated/actual)

#### Lua Scripts
- `lua_script_executions_total` - Script executions (success/error)
- `lua_script_duration_seconds` - Script execution duration (histogram)

### Logging

All abuse prevention events are logged:

- **Rate limit violations**: Warning level
- **Challenge validation failures**: Warning level
- **Turnstile failures**: Warning level
- **Cost throttling triggers**: Warning level
- **Progressive bans**: Warning level

### Alerting

Consider setting up alerts for:
- High rate limit rejection rates
- Frequent challenge validation failures
- Cost throttling triggers
- Lua script errors

---

## Security Best Practices

1. **Always use Cloudflare** when possible - `CF-Connecting-IP` cannot be spoofed
2. **Never trust `X-Forwarded-For`** without a properly configured reverse proxy
3. **Enable challenge-response** in production to prevent fingerprint replay
4. **Monitor cost throttling** to detect abuse patterns
5. **Review rate limit settings** regularly based on traffic patterns
6. **Test progressive bans** to ensure they're working correctly
7. **Monitor Lua script errors** - they indicate Redis issues
8. **Keep webhook secrets secure** - rotate regularly
9. **Enable Turnstile** for additional bot protection
10. **Review input sanitization logs** for injection attempts

---

## Troubleshooting

### Rate Limiting Not Working

**Symptoms:**
- Users bypassing rate limits
- Limits not enforced

**Possible Causes:**
1. `TRUST_X_FORWARDED_FOR=true` but reverse proxy not configured
2. Redis connection issues
3. Lua script errors

**Solutions:**
- Verify reverse proxy strips user-supplied headers
- Check Redis connectivity
- Review Lua script error logs

### Challenges Not Validating

**Symptoms:**
- Challenge validation always fails
- "Invalid challenge" errors

**Possible Causes:**
1. Challenge expired (TTL too short)
2. Redis connection issues
3. Challenge consumed twice (race condition)

**Solutions:**
- Increase `CHALLENGE_TTL_SECONDS`
- Check Redis connectivity
- Review challenge validation logs

### Cost Throttling Too Aggressive

**Symptoms:**
- Legitimate users getting throttled
- Thresholds too low

**Solutions:**
- Increase `HIGH_COST_THRESHOLD_USD`
- Increase `DAILY_COST_LIMIT_USD`
- Review cost estimation accuracy

---

## Related Documentation

- [Fingerprinting Review](./FINGERPRINTING_REVIEW.md) - Detailed fingerprinting implementation review
- [Rate Limiting Security](./RATE_LIMITING_SECURITY.md) - IP spoofing prevention
- [Red Team Assessment](./RED_TEAM_ASSESSMENT_NOV_2025.md) - Security audit results
- [Environment Variables](../setup/ENVIRONMENT_VARIABLES.md) - Configuration reference

---

## References

- [Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/)
- [Redis Lua Scripting](https://redis.io/docs/manual/programmability/eval-intro/)
- [OWASP Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html)
- [Sliding Window Rate Limiting](https://en.wikipedia.org/wiki/Sliding_window_protocol)

