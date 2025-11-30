"""
Redis Lua scripts for atomic operations.

These scripts consolidate multiple Redis operations into single atomic transactions,
eliminating race conditions and reducing network round-trips.
"""

COST_THROTTLE_LUA = """
-- Atomic cost throttling check
-- Keys: [1] cost_key (window ZSET), [2] daily_cost_key (daily ZSET with date), [3] throttle_marker_key
-- Args: [1] now (timestamp), [2] window_seconds, [3] estimated_cost, [4] threshold, [5] daily_limit, [6] throttle_duration, [7] unique_member, [8] daily_ttl

-- Helper function to extract cost from member string
-- Member format: "fp:challenge:hash:cost" or "hash:cost"
-- Returns cost value or nil if parsing fails
local function extract_cost(member_str)
    -- Find last colon position
    local last_colon_pos = 0
    local pos = 1
    while true do
        local colon_pos = string.find(member_str, ':', pos, true)
        if colon_pos then
            last_colon_pos = colon_pos
            pos = colon_pos + 1
        else
            break
        end
    end
    
    if last_colon_pos > 0 then
        -- Extract cost part (after last colon)
        local cost_str = string.sub(member_str, last_colon_pos + 1)
        return tonumber(cost_str)
    else
        -- No colon found, try parsing entire member as cost
        return tonumber(member_str)
    end
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
local daily_ttl = tonumber(ARGV[8])

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
local all_costs = redis.call('ZRANGE', cost_key, 0, -1, 'WITHSCORES')
local total_cost_in_window = 0.0

for i = 1, #all_costs, 2 do
    local member = all_costs[i]
    local member_str = tostring(member)
    local cost_value = extract_cost(member_str)
    
    -- Defensive parsing: only add positive costs
    if cost_value and cost_value > 0 then
        total_cost_in_window = total_cost_in_window + cost_value
    end
end

-- Calculate total daily cost
local daily_costs = redis.call('ZRANGE', daily_cost_key, 0, -1, 'WITHSCORES')
local total_daily_cost = 0.0

for i = 1, #daily_costs, 2 do
    local member = daily_costs[i]
    local member_str = tostring(member)
    local cost_value = extract_cost(member_str)
    
    -- Defensive parsing: only add positive costs
    if cost_value and cost_value > 0 then
        total_daily_cost = total_daily_cost + cost_value
    end
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
-- Keys: [1] cost_key (window ZSET), [2] daily_cost_key (daily ZSET with date)
-- Args: [1] now (timestamp), [2] unique_member, [3] window_ttl, [4] daily_ttl

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

