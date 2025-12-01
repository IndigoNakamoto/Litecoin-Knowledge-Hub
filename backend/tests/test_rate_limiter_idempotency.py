"""
Idempotency verification test suite for rate limiter.

This test suite uses fakeredis to verify that the Smart Deduplication
actually works, simulating real-world scenarios like double-clicks.
"""

import pytest
import time
from unittest.mock import AsyncMock

# Try to import fakeredis, but skip tests if not available
try:
    from fakeredis.aioredis import FakeRedis
    FAKEREDIS_AVAILABLE = True
except ImportError:
    FAKEREDIS_AVAILABLE = False
    FakeRedis = None

from backend.utils.lua_scripts import SLIDING_WINDOW_LUA

# Mock Configuration
WINDOW_SECONDS = 60
LIMIT = 5
EXPIRE_SECONDS = 120


# Use pytest_asyncio.fixture if available, otherwise pytest.fixture
try:
    import pytest_asyncio
    async_fixture = pytest_asyncio.fixture
except ImportError:
    async_fixture = pytest.fixture


@async_fixture
async def redis_client():
    """Create a fake Redis client for testing."""
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available, install with: pip install fakeredis")
    
    redis = FakeRedis(decode_responses=False)  # Return bytes like real Redis
    yield redis
    await redis.close()


@pytest.mark.asyncio
async def test_sliding_window_normal_flow(redis_client):
    """Test standard requests under limit."""
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available")
    
    key = "test:window:1"
    now = int(time.time())
    
    # 1. First Request
    res = await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,  # numkeys
        key,
        now,
        WINDOW_SECONDS,
        LIMIT,
        "user1",
        EXPIRE_SECONDS
    )
    assert res[0] == 1  # Allowed
    assert res[1] == 1  # Count 1
    
    # 2. Second Request (Different User)
    res = await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        now,
        WINDOW_SECONDS,
        LIMIT,
        "user2",
        EXPIRE_SECONDS
    )
    assert res[0] == 1
    assert res[1] == 2  # Count 2


@pytest.mark.asyncio
async def test_idempotency_double_click(redis_client):
    """
    CRITICAL: Verify that the SAME member_id sent twice 
    does NOT increase the count (Double-Click Protection).
    
    This is the core idempotency test - ensures double-clicks
    with the same fingerprint/challenge are counted as ONE request.
    """
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available")
    
    key = "test:window:dedup"
    now = int(time.time())
    fingerprint = "fp:challenge_A:hash_X"  # Full fingerprint including challenge
    
    # 1. Initial Request
    res = await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        now,
        WINDOW_SECONDS,
        LIMIT,
        fingerprint,
        EXPIRE_SECONDS
    )
    assert res[0] == 1  # Allowed
    assert res[1] == 1  # Count 1
    
    # 2. "Double Click" - Same fingerprint, same challenge, 100ms later
    # This simulates a user accidentally clicking twice quickly
    res = await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        now + 1,  # 1 second later (simulating quick double-click)
        WINDOW_SECONDS,
        LIMIT,
        fingerprint,  # SAME fingerprint
        EXPIRE_SECONDS
    )
    
    assert res[0] == 1  # Still Allowed (idempotency)
    assert res[1] == 1  # Count MUST remain 1 (Not 2) - This is the critical assertion
    
    # Verify Score Updated (Sliding window extended)
    score = await redis_client.zscore(key, fingerprint)
    assert int(score) == now + 1  # Timestamp updated to latest


@pytest.mark.asyncio
async def test_idempotency_different_challenges(redis_client):
    """
    Verify that DIFFERENT challenges with the same stable hash
    DO count separately (not deduplicated).
    
    This ensures users can't bypass limits by getting new challenges,
    but double-clicks with the same challenge are still deduplicated.
    """
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available")
    
    key = "test:window:challenges"
    now = int(time.time())
    stable_hash = "hash_X"
    
    # Request 1: Challenge A
    fingerprint1 = f"fp:challenge_A:{stable_hash}"
    res = await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        now,
        WINDOW_SECONDS,
        LIMIT,
        fingerprint1,
        EXPIRE_SECONDS
    )
    assert res[0] == 1
    assert res[1] == 1
    
    # Request 2: Challenge B (different challenge, same stable hash)
    fingerprint2 = f"fp:challenge_B:{stable_hash}"
    res = await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        now + 1,
        WINDOW_SECONDS,
        LIMIT,
        fingerprint2,
        EXPIRE_SECONDS
    )
    assert res[0] == 1
    assert res[1] == 2  # Count increases - different challenges count separately
    
    # Request 3: Double-click with Challenge A again
    res = await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        now + 2,
        WINDOW_SECONDS,
        LIMIT,
        fingerprint1,  # Same as Request 1
        EXPIRE_SECONDS
    )
    assert res[0] == 1
    assert res[1] == 2  # Count remains 2 - deduplicated (same challenge)


@pytest.mark.asyncio
async def test_rejection_precision(redis_client):
    """Test rejection and precise retry_after calculation."""
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available")
    
    key = "test:window:limit"
    start_time = 1000
    limit = 2
    
    # Fill bucket
    await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        start_time,
        WINDOW_SECONDS,
        limit,
        "u1",
        EXPIRE_SECONDS
    )
    await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        start_time + 10,
        WINDOW_SECONDS,
        limit,
        "u2",
        EXPIRE_SECONDS
    )
    
    # Request 3 (Should be blocked)
    now = start_time + 20
    res = await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        now,
        WINDOW_SECONDS,
        limit,
        "u3",
        EXPIRE_SECONDS
    )
    
    allowed, count, oldest_ts = res
    
    assert allowed == 0  # Rejected
    assert count == 2  # Still at limit
    assert oldest_ts == start_time  # Should return timestamp of "u1"
    
    # Calculate retry_after in Python
    retry_after = WINDOW_SECONDS - (now - oldest_ts)
    # Window=60, Now=1020, Oldest=1000. Diff=20. Retry=40.
    assert retry_after == 40


@pytest.mark.asyncio
async def test_idempotency_retry_scenario(redis_client):
    """
    Test that network retries with the same fingerprint are deduplicated.
    
    Simulates a scenario where:
    1. User sends request
    2. Network fails/timeout
    3. Frontend retries with same fingerprint
    4. Should be counted as ONE request, not two
    """
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available")
    
    key = "test:window:retry"
    now = int(time.time())
    fingerprint = "fp:challenge_retry:hash_retry"
    
    # Initial request
    res = await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        now,
        WINDOW_SECONDS,
        LIMIT,
        fingerprint,
        EXPIRE_SECONDS
    )
    assert res[0] == 1
    assert res[1] == 1
    
    # Network retry 5 seconds later (same fingerprint)
    res = await redis_client.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        now + 5,
        WINDOW_SECONDS,
        LIMIT,
        fingerprint,  # Same fingerprint
        EXPIRE_SECONDS
    )
    
    assert res[0] == 1  # Allowed (idempotency)
    assert res[1] == 1  # Count remains 1 - retry deduplicated


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

