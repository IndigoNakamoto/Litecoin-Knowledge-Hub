"""
Atomic Rate Limiting Verification Suite

This test suite uses fakeredis to verify that the atomic Lua scripts
work correctly, including idempotency (double-click protection) and
cost parsing safety with complex formats.

Install requirements: pip install pytest pytest-asyncio fakeredis
"""

import pytest
import time

# Try to import fakeredis, but skip tests if not available
try:
    from fakeredis.aioredis import FakeRedis
    FAKEREDIS_AVAILABLE = True
except ImportError:
    FAKEREDIS_AVAILABLE = False
    FakeRedis = None

from backend.utils.lua_scripts import SLIDING_WINDOW_LUA, COST_THROTTLE_LUA

# Use pytest_asyncio.fixture if available, otherwise pytest.fixture
try:
    import pytest_asyncio
    async_fixture = pytest_asyncio.fixture
except ImportError:
    async_fixture = pytest.fixture


@async_fixture
async def redis():
    """Create a fake Redis client for testing."""
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available, install with: pip install fakeredis")
    
    r = FakeRedis(decode_responses=False)  # Return bytes like real Redis
    yield r
    await r.close()


@pytest.mark.asyncio
async def test_sliding_window_idempotency(redis):
    """
    Verifies that sending the same fingerprint twice (double-click)
    does NOT increment the count but DOES allow the request.
    
    This is the CRITICAL test for double-click protection.
    """
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available")
    
    key = "rl:test:window"
    now = 1700000000
    window = 60
    limit = 5
    fingerprint = "user_123_hash"
    
    # 1. First Request
    # Returns: [allowed, count, oldest_ts]
    res1 = await redis.eval(SLIDING_WINDOW_LUA, 1, key, now, window, limit, fingerprint, 120)
    assert res1[0] == 1  # Allowed
    assert res1[1] == 1  # Count is 1
    
    # 2. Second Request (Same fingerprint, 1 second later)
    # This simulates a user hitting refresh or double-clicking
    res2 = await redis.eval(SLIDING_WINDOW_LUA, 1, key, now + 1, window, limit, fingerprint, 120)
    
    assert res2[0] == 1  # Still Allowed
    assert res2[1] == 1  # Count is STILL 1 (Critical Check - idempotency)
    assert res2[2] == 0  # oldest_ts is 0 for allowed requests
    
    # 3. Different User
    res3 = await redis.eval(SLIDING_WINDOW_LUA, 1, key, now + 2, window, limit, "other_user", 120)
    assert res3[0] == 1
    assert res3[1] == 2  # Count increments for different user


@pytest.mark.asyncio
async def test_cost_parsing_safety(redis):
    """
    Verifies the Lua script safely parses costs even with complex fingerprints
    (like IPv6) or missing colons.
    
    This tests the safer string.match pattern that handles edge cases.
    """
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available")
    
    cost_key = "cost:window"
    daily_key = "cost:daily:2025-01-30"
    throttle_key = "cost:throttle"
    now = 1700000000
    
    # Args: now, window, est_cost, threshold, daily_limit, throttle_dur, member, ttl
    args = [now, 600, 0.01, 1.0, 5.0, 60, "test_member", 86400]
    
    # 1. Standard format "fp:hash:cost"
    member_standard = "fp:abc:0.05"
    args[2] = 0.05  # est cost
    args[6] = member_standard
    res1 = await redis.eval(COST_THROTTLE_LUA, 3, cost_key, daily_key, throttle_key, *args)
    assert res1[0] == 0  # Allowed (status 0 = success)
    
    # 2. IPv6 format "2001:db8::1:0.05" (Colon heavy)
    member_ipv6 = "2001:db8::1:0.05"
    args[6] = member_ipv6
    res2 = await redis.eval(COST_THROTTLE_LUA, 3, cost_key, daily_key, throttle_key, *args)
    assert res2[0] == 0  # Allowed
    
    # 3. No colon "0.05" (Direct cost)
    member_raw = "0.05"
    args[6] = member_raw
    res3 = await redis.eval(COST_THROTTLE_LUA, 3, cost_key, daily_key, throttle_key, *args)
    assert res3[0] == 0  # Allowed
    
    # Calculate Total
    # We added 0.05 three times. Total should be 0.15
    # The Lua script sums them up internally. Let's trigger a threshold check to verify.
    
    # Set threshold to 0.16 (should allow one more 0.01 request)
    args[3] = 0.16
    args[2] = 0.005
    args[6] = "fp:test:0.005"
    res4 = await redis.eval(COST_THROTTLE_LUA, 3, cost_key, daily_key, throttle_key, *args)
    assert res4[0] == 0  # Allowed (total ~0.155 < 0.16)
    
    # Set threshold to 0.10 (should fail, as we are at ~0.155)
    args[3] = 0.10
    res5 = await redis.eval(COST_THROTTLE_LUA, 3, cost_key, daily_key, throttle_key, *args)
    assert res5[0] == 3  # Throttled by Window (status 3 = window threshold exceeded)


@pytest.mark.asyncio
async def test_sliding_window_rejection_precision(redis):
    """
    Verifies that rejected requests return the oldest timestamp
    for precise retry_after calculation.
    """
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available")
    
    key = "rl:test:precision"
    start_time = 1000
    limit = 2
    
    # Fill bucket
    await redis.eval(SLIDING_WINDOW_LUA, 1, key, start_time, 60, limit, "u1", 120)
    await redis.eval(SLIDING_WINDOW_LUA, 1, key, start_time + 10, 60, limit, "u2", 120)
    
    # Request 3 (Should be blocked)
    now = start_time + 20
    res = await redis.eval(SLIDING_WINDOW_LUA, 1, key, now, 60, limit, "u3", 120)
    
    allowed, count, oldest_ts = res
    
    assert allowed == 0  # Rejected
    assert count == 2  # Still at limit
    assert oldest_ts == start_time  # Should return timestamp of "u1"
    
    # Calculate retry_after in Python
    retry_after = 60 - (now - oldest_ts)
    # Window=60, Now=1020, Oldest=1000. Diff=20. Retry=40.
    assert retry_after == 40


@pytest.mark.asyncio
async def test_sliding_window_different_users(redis):
    """
    Verifies that different users (different fingerprints) count separately.
    """
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available")
    
    key = "rl:test:different"
    now = 1700000000
    window = 60
    limit = 5
    
    # Request 1: User A
    res1 = await redis.eval(SLIDING_WINDOW_LUA, 1, key, now, window, limit, "user_a", 120)
    assert res1[0] == 1
    assert res1[1] == 1
    
    # Request 2: User B (different fingerprint)
    res2 = await redis.eval(SLIDING_WINDOW_LUA, 1, key, now + 1, window, limit, "user_b", 120)
    assert res2[0] == 1
    assert res2[1] == 2  # Count increments
    
    # Request 3: User A again (same fingerprint, should deduplicate)
    res3 = await redis.eval(SLIDING_WINDOW_LUA, 1, key, now + 2, window, limit, "user_a", 120)
    assert res3[0] == 1
    assert res3[1] == 2  # Count remains 2 (deduplicated)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

