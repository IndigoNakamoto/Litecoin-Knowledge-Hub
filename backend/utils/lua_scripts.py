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

