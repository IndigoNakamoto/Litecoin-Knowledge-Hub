"""
Redis Lua scripts for atomic operations.

These scripts consolidate multiple Redis operations into single atomic transactions,
eliminating race conditions and reducing network round-trips.
"""

COST_THROTTLE_LUA = """
-- Atomic cost throttling check
-- Keys: [1] cost_key (window ZSET), [2] daily_cost_key (daily ZSET with date suffix, e.g., "llm:cost:daily:hash:2025-01-30"), [3] throttle_marker_key
-- Args: [1] now (timestamp), [2] window_seconds, [3] estimated_cost, [4] threshold, [5] daily_limit, [6] throttle_duration, [7] unique_member, [8] daily_ttl
-- Note: KEYS[2] is passed with date suffix from Python (daily_cost_key_with_date), so daily tracking is correctly isolated by date

-- Helper function to extract cost from member string
-- Member format: "fp:challenge:hash:cost" or "hash:cost"
-- Returns cost value or 0 if parsing fails (safer for arithmetic)
-- Uses safer pattern matching instead of manual string scanning
local function extract_cost(member_str)
    -- Extract last part after final colon using pattern matching
    -- This is much safer than manual string.find loops and handles IPv6/colon-heavy formats
    local cost_str = member_str:match("([^:]+)$")
    if not cost_str then
        -- No colon found, try parsing entire member as cost
        local cost = tonumber(member_str)
        return (cost and cost > 0) and cost or 0
    end
    local cost = tonumber(cost_str)
    -- Return 0 for invalid values (safer for arithmetic than nil)
    return (cost and cost > 0) and cost or 0
end

local cost_key = KEYS[1]
local daily_cost_key = KEYS[2]
local throttle_marker_key = KEYS[3]

local now = tonumber(ARGV[1])
local window_seconds = tonumber(ARGV[2])
local estimated_cost = tonumber(ARGV[3])
local threshold = tonumber(ARGV[4])
local daily_limit = tonumber(ARGV[5])
local throttle_duration = tonumber(ARGV[6])
local unique_member = ARGV[7]
local     daily_ttl = tonumber(ARGV[8])

-- Validate daily_ttl (ensure at least 3 days for safety)
if daily_ttl < 259200 then
    daily_ttl = 259200  -- 3 days minimum
end

-- Check if already throttled (using TTL for accuracy)
local throttle_ttl = redis.call('TTL', throttle_marker_key)
if throttle_ttl > 0 then
    -- Still throttled, return remaining TTL
    return {1, throttle_ttl}
elseif throttle_ttl == -1 then
    -- Key exists but has no expiration (unexpected, but handle gracefully)
    -- Delete it and continue (treat as not throttled)
    redis.call('DEL', throttle_marker_key)
end
-- throttle_ttl == -2 means key doesn't exist, continue normally

-- Remove expired entries from window (older than window_seconds)
local cutoff = now - window_seconds
redis.call('ZREMRANGEBYSCORE', cost_key, 0, cutoff)

-- Calculate total cost in window
-- Use ZRANGE without WITHSCORES since we only need members for cost extraction (more efficient)
local all_costs = redis.call('ZRANGE', cost_key, 0, -1)
local total_cost_in_window = 0.0

for _, member in ipairs(all_costs) do
    local member_str = tostring(member)
    local cost_value = extract_cost(member_str)
    -- extract_cost already returns 0 for invalid values, so safe to add directly
    total_cost_in_window = total_cost_in_window + cost_value
end

-- Calculate total daily cost
-- Use ZRANGE without WITHSCORES since we only need members for cost extraction (more efficient)
local daily_costs = redis.call('ZRANGE', daily_cost_key, 0, -1)
local total_daily_cost = 0.0

for _, member in ipairs(daily_costs) do
    local member_str = tostring(member)
    local cost_value = extract_cost(member_str)
    -- extract_cost already returns 0 for invalid values, so safe to add directly
    total_daily_cost = total_daily_cost + cost_value
end

-- Check daily limit first (hard cap)
local new_daily_cost = total_daily_cost + estimated_cost
if new_daily_cost >= daily_limit then
    -- Daily limit exceeded - set throttle marker with 2x duration
    redis.call('SETEX', throttle_marker_key, throttle_duration * 2, now)
    return {2, throttle_duration * 2}
end

-- Check window threshold
local new_total_cost = total_cost_in_window + estimated_cost
if new_total_cost >= threshold then
    -- Window threshold exceeded - set throttle marker
    redis.call('SETEX', throttle_marker_key, throttle_duration, now)
    return {3, throttle_duration}
end

-- Request allowed - record in both window and daily ZSETs atomically
redis.call('ZADD', cost_key, now, unique_member)
redis.call('EXPIRE', cost_key, window_seconds + 60)

redis.call('ZADD', daily_cost_key, now, unique_member)
redis.call('EXPIRE', daily_cost_key, daily_ttl)

-- Return success
return {0, 0}
"""

RECORD_COST_LUA = """
-- Atomic cost recording
-- Keys: [1] cost_key (window ZSET), [2] daily_cost_key (daily ZSET with date suffix, e.g., "llm:cost:daily:hash:2025-01-30")
-- Args: [1] now (timestamp), [2] unique_member, [3] window_ttl, [4] daily_ttl
-- Note: KEYS[2] is passed with date suffix from Python (daily_cost_key_with_date), so daily tracking is correctly isolated by date

local cost_key = KEYS[1]
local daily_cost_key = KEYS[2]

local now = tonumber(ARGV[1])
local unique_member = ARGV[2]
local window_ttl = tonumber(ARGV[3])
local daily_ttl = tonumber(ARGV[4])

-- Record in window ZSET
redis.call('ZADD', cost_key, now, unique_member)
redis.call('EXPIRE', cost_key, window_ttl)

-- Record in daily ZSET
redis.call('ZADD', daily_cost_key, now, unique_member)
redis.call('EXPIRE', daily_cost_key, daily_ttl)

return 0
"""

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
    -- Do NOT increment count - this is idempotency/deduplication
    -- ZADD with existing member only updates score, doesn't change cardinality
    redis.call('ZADD', key, now, member_id)
    redis.call('EXPIRE', key, expire_seconds)
    return {1, count, 0} -- 1 = Allowed (Duplicate), count unchanged, retry_after=0
elseif count < limit then
    -- CASE B: Under limit, new request
    -- Add user
    redis.call('ZADD', key, now, member_id)
    redis.call('EXPIRE', key, expire_seconds)
    return {1, count + 1, 0} -- 1 = Allowed (New), count+1, retry_after=0
else
    -- CASE C: Over limit, new request
    -- REJECT
    -- Return oldest timestamp for precise retry_after calculation (avoids extra round-trip)
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local oldest_ts = now  -- Default to now if no entries (shouldn't happen if count > 0)
    if oldest and #oldest > 1 then
        oldest_ts = tonumber(oldest[2])
    end
    return {0, count, oldest_ts} -- 0 = Rejected, count, oldest_timestamp
end
"""

VALIDATE_CONSUME_CHALLENGE_LUA = """
-- Atomic Challenge Validation and Consumption
-- Prevents TOCTOU race condition where two concurrent requests could both validate
-- the same challenge before either deletes it.
--
-- Keys: [1] challenge_key (challenge:{challenge_id}), [2] active_challenges_key (challenge:active:{identifier})
-- Args: [1] expected_identifier, [2] challenge_id
-- Returns: [status_code, stored_identifier_or_nil]
--   status_code: 0=success (consumed), 1=not_found, 2=identifier_mismatch

local challenge_key = KEYS[1]
local active_challenges_key = KEYS[2]
local expected_identifier = ARGV[1]
local challenge_id = ARGV[2]

-- Atomic GET - check if challenge exists
local stored_identifier = redis.call('GET', challenge_key)
if not stored_identifier then
    -- Challenge not found or already consumed
    return {1, nil}
end

-- Verify the challenge was issued to this identifier
if stored_identifier ~= expected_identifier then
    -- Identifier mismatch - possible replay attack attempt
    -- Do NOT consume the challenge, just report mismatch
    return {2, stored_identifier}
end

-- Challenge valid - consume it atomically
-- DELETE the challenge key (one-time use)
redis.call('DEL', challenge_key)

-- Remove from active challenges set for this identifier
redis.call('ZREM', active_challenges_key, challenge_id)

-- Return success with the stored identifier
return {0, stored_identifier}
"""

GENERATE_CHALLENGE_LUA = """
-- Atomic Challenge Generation
-- Prevents race condition where multiple concurrent requests could all pass the count check
-- before any challenge is added, bypassing max_active_challenges_per_identifier.
--
-- Keys: [1] active_challenges_key, [2] challenge_key, [3] violation_count_key, [4] ban_key
-- Args: [1] now, [2] ttl, [3] max_active, [4] challenge_id, [5] identifier, [6] expiry_time,
--       [7] ban_durations (comma-separated, e.g. "60,300")
-- Returns: [status_code, data1, data2]
--   status_code: 0=success, 1=limit_exceeded, 2=banned
--   For status 0: [0, 0, 0]
--   For status 1: [1, violation_count, ban_duration]
--   For status 2: [2, retry_after, violation_count]

local active_challenges_key = KEYS[1]
local challenge_key = KEYS[2]
local violation_count_key = KEYS[3]
local ban_key = KEYS[4]

local now = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])
local max_active = tonumber(ARGV[3])
local challenge_id = ARGV[4]
local identifier = ARGV[5]
local expiry_time = tonumber(ARGV[6])
local ban_durations_str = ARGV[7]

-- Parse ban durations from comma-separated string
local ban_durations = {}
for d in string.gmatch(ban_durations_str, "([^,]+)") do
    table.insert(ban_durations, tonumber(d))
end

-- Check if currently banned
local ban_expiry = redis.call('GET', ban_key)
if ban_expiry then
    ban_expiry = tonumber(ban_expiry)
    if ban_expiry > now then
        -- Still banned
        local retry_after = ban_expiry - now
        local violation_count = redis.call('GET', violation_count_key)
        violation_count = violation_count and tonumber(violation_count) or 1
        return {2, retry_after, violation_count}
    else
        -- Ban expired, clean it up
        redis.call('DEL', ban_key)
    end
end

-- Cleanup expired challenges from active set
redis.call('ZREMRANGEBYSCORE', active_challenges_key, 0, now - ttl)

-- Check current active challenge count
local current_count = redis.call('ZCARD', active_challenges_key)
if current_count >= max_active then
    -- Limit exceeded - increment violations and apply ban atomically
    local violation_count = redis.call('INCR', violation_count_key)
    redis.call('EXPIRE', violation_count_key, 3600)  -- Keep violation count for 1 hour
    
    -- Determine ban duration based on violation count (progressive)
    local ban_index = math.min(violation_count, #ban_durations)
    local ban_duration = ban_durations[ban_index] or ban_durations[#ban_durations] or 60
    local new_ban_expiry = now + ban_duration
    
    -- Apply ban
    redis.call('SETEX', ban_key, ban_duration, new_ban_expiry)
    
    return {1, violation_count, ban_duration}
end

-- All checks passed - create challenge atomically
-- Store challenge in Redis with TTL
redis.call('SETEX', challenge_key, ttl, identifier)

-- Add to active challenges sorted set (score is expiry time)
redis.call('ZADD', active_challenges_key, expiry_time, challenge_id)
redis.call('EXPIRE', active_challenges_key, ttl + 60)

-- Reset violation count on successful generation (reward good behavior)
-- Only if there was a previous violation count and no active ban
local existing_violations = redis.call('GET', violation_count_key)
if existing_violations then
    local active_ban = redis.call('GET', ban_key)
    if not active_ban then
        redis.call('DEL', violation_count_key)
    end
end

return {0, 0, 0}
"""

CHECK_AND_RESERVE_SPEND_LUA = """
-- Atomic Spend Limit Check and Reservation
-- Prevents race condition where multiple concurrent requests could all pass the limit
-- check before any spend is recorded, leading to budget overruns.
--
-- Keys: [1] daily_cost_key, [2] hourly_cost_key
-- Args: [1] buffered_cost, [2] daily_limit, [3] hourly_limit, [4] daily_ttl, [5] hourly_ttl
-- Returns: [status_code, daily_cost, hourly_cost]
--   status_code: 0=allowed (reserved), 1=daily_limit_exceeded, 2=hourly_limit_exceeded

local daily_key = KEYS[1]
local hourly_key = KEYS[2]

local buffered_cost = tonumber(ARGV[1])
local daily_limit = tonumber(ARGV[2])
local hourly_limit = tonumber(ARGV[3])
local daily_ttl = tonumber(ARGV[4])
local hourly_ttl = tonumber(ARGV[5])

-- Get current costs (default to 0 if keys don't exist)
local daily_cost = tonumber(redis.call('GET', daily_key) or "0")
local hourly_cost = tonumber(redis.call('GET', hourly_key) or "0")

-- Check daily limit first
if (daily_cost + buffered_cost) > daily_limit then
    -- Daily limit would be exceeded
    return {1, daily_cost, hourly_cost}
end

-- Check hourly limit
if (hourly_cost + buffered_cost) > hourly_limit then
    -- Hourly limit would be exceeded
    return {2, daily_cost, hourly_cost}
end

-- Both limits OK - reserve the spend atomically
redis.call('INCRBYFLOAT', daily_key, buffered_cost)
redis.call('INCRBYFLOAT', hourly_key, buffered_cost)

-- Set TTLs
redis.call('EXPIRE', daily_key, daily_ttl)
redis.call('EXPIRE', hourly_key, hourly_ttl)

-- Return success with new costs
return {0, daily_cost + buffered_cost, hourly_cost + buffered_cost}
"""

ADJUST_SPEND_LUA = """
-- Atomic Spend Adjustment
-- Adjusts previously reserved spend to actual cost.
-- Use positive adjustment to add more, negative to refund overestimate.
--
-- Keys: [1] daily_cost_key, [2] hourly_cost_key, [3] daily_token_key, [4] hourly_token_key
-- Args: [1] cost_adjustment, [2] input_tokens, [3] output_tokens, [4] daily_ttl, [5] hourly_ttl
-- Returns: [daily_cost, hourly_cost]

local daily_key = KEYS[1]
local hourly_key = KEYS[2]
local daily_token_key = KEYS[3]
local hourly_token_key = KEYS[4]

local cost_adjustment = tonumber(ARGV[1])
local input_tokens = tonumber(ARGV[2])
local output_tokens = tonumber(ARGV[3])
local daily_ttl = tonumber(ARGV[4])
local hourly_ttl = tonumber(ARGV[5])

-- Adjust costs (can be negative to refund overestimate)
local daily_cost = redis.call('INCRBYFLOAT', daily_key, cost_adjustment)
local hourly_cost = redis.call('INCRBYFLOAT', hourly_key, cost_adjustment)

-- Set TTLs for cost keys
redis.call('EXPIRE', daily_key, daily_ttl)
redis.call('EXPIRE', hourly_key, hourly_ttl)

-- Record token counts
if input_tokens > 0 then
    redis.call('HINCRBY', daily_token_key, 'input', input_tokens)
    redis.call('HINCRBY', hourly_token_key, 'input', input_tokens)
end

if output_tokens > 0 then
    redis.call('HINCRBY', daily_token_key, 'output', output_tokens)
    redis.call('HINCRBY', hourly_token_key, 'output', output_tokens)
end

-- Set TTLs for token keys (only if we updated them)
if input_tokens > 0 or output_tokens > 0 then
    redis.call('EXPIRE', daily_token_key, daily_ttl)
    redis.call('EXPIRE', hourly_token_key, hourly_ttl)
end

return {tonumber(daily_cost), tonumber(hourly_cost)}
"""

APPLY_PROGRESSIVE_BAN_LUA = """
-- Atomic Progressive Ban Application
-- Consolidates violation increment, expiry setting, and ban application into a single
-- atomic operation. Eliminates race conditions on violation count and ensures
-- consistent ban duration calculation.
--
-- Keys: [1] violation_key, [2] ban_key
-- Args: [1] now (timestamp), [2] ban_durations (comma-separated, e.g. "60,300,900,3600"),
--       [3] violation_ttl (seconds to keep violation count)
-- Returns: [violation_count, ban_expiry, ban_duration]

local violation_key = KEYS[1]
local ban_key = KEYS[2]

local now = tonumber(ARGV[1])
local ban_durations_str = ARGV[2]
local violation_ttl = tonumber(ARGV[3])

-- Parse ban durations from comma-separated string
local ban_durations = {}
for d in string.gmatch(ban_durations_str, "([^,]+)") do
    table.insert(ban_durations, tonumber(d))
end

-- Atomic increment of violation count
local violation_count = redis.call('INCR', violation_key)
redis.call('EXPIRE', violation_key, violation_ttl)

-- Determine ban duration based on violation count (progressive)
-- violation_count is 1-indexed, ban_durations is also 1-indexed in Lua
local ban_index = math.min(violation_count, #ban_durations)
local ban_duration = ban_durations[ban_index] or ban_durations[#ban_durations] or 60

-- Calculate ban expiry
local ban_expiry = now + ban_duration

-- Apply ban atomically
redis.call('SETEX', ban_key, ban_duration, ban_expiry)

return {violation_count, ban_expiry, ban_duration}
"""

