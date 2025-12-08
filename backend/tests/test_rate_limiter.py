#!/usr/bin/env python3
"""
Test script for rate limiting functionality.

This script tests the rate limiting implementation by:
1. Testing sliding window rate limiting accuracy
2. Testing progressive ban application
3. Testing ban expiration
4. Testing Cloudflare header handling
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
backend_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path_actual = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path_actual):
    load_dotenv(dotenv_path=dotenv_path_actual, override=True)

# Add project root to path
project_root_dir = os.path.dirname(backend_dir)
sys.path.insert(0, project_root_dir)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from fastapi.testclient import TestClient

from backend.rate_limiter import (
    RateLimitConfig,
    check_rate_limit,
    _get_ip_from_request,
    _check_progressive_ban,
    _apply_progressive_ban,
    _check_sliding_window,
)


def test_rate_limit_config_defaults():
    """Test that RateLimitConfig has correct defaults for progressive limits."""
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test"
    )
    
    assert config.enable_progressive_limits == True
    assert config.progressive_ban_durations == [60, 300, 900, 3600]


def test_rate_limit_config_custom_progressive():
    """Test that RateLimitConfig accepts custom progressive ban durations."""
    custom_durations = [30, 120, 600]
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test",
        progressive_ban_durations=custom_durations
    )
    
    assert config.progressive_ban_durations == custom_durations


def test_get_ip_from_request_cloudflare():
    """Test IP extraction with Cloudflare header (always trusted)."""
    request = MagicMock(spec=Request)
    request.headers = {"CF-Connecting-IP": "192.168.1.100"}
    request.client = None
    
    # Cloudflare header should always be trusted, regardless of TRUST_X_FORWARDED_FOR
    ip = _get_ip_from_request(request)
    assert ip == "192.168.1.100"
    
    # Test that CF-Connecting-IP takes precedence over X-Forwarded-For
    request.headers = {
        "CF-Connecting-IP": "192.168.1.100",
        "X-Forwarded-For": "10.0.0.1"
    }
    with patch.dict(os.environ, {"TRUST_X_FORWARDED_FOR": "true"}):
        ip = _get_ip_from_request(request)
        assert ip == "192.168.1.100"  # CF-Connecting-IP should win


def test_get_ip_from_request_x_forwarded_for():
    """Test IP extraction with X-Forwarded-For header (only when trusted)."""
    request = MagicMock(spec=Request)
    request.headers = {"X-Forwarded-For": "192.168.1.200, 10.0.0.1"}
    request.client = None
    
    # Test with TRUST_X_FORWARDED_FOR enabled
    with patch.dict(os.environ, {"TRUST_X_FORWARDED_FOR": "true"}):
        ip = _get_ip_from_request(request)
        assert ip == "192.168.1.200"
    
    # Test with TRUST_X_FORWARDED_FOR disabled (default behavior)
    # Should fall back to "unknown" since client is None
    with patch.dict(os.environ, {"TRUST_X_FORWARDED_FOR": "false"}, clear=False):
        ip = _get_ip_from_request(request)
        assert ip == "unknown"


def test_get_ip_from_request_direct():
    """Test IP extraction from direct client connection."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    
    ip = _get_ip_from_request(request)
    assert ip == "127.0.0.1"


def test_get_ip_from_request_invalid_ip():
    """Test IP extraction with invalid IP addresses (should be rejected)."""
    request = MagicMock(spec=Request)
    request.client = None
    
    # Test invalid CF-Connecting-IP
    request.headers = {"CF-Connecting-IP": "not.an.ip.address"}
    ip = _get_ip_from_request(request)
    assert ip == "unknown"
    
    # Test invalid X-Forwarded-For (when trusted)
    request.headers = {"X-Forwarded-For": "invalid-ip"}
    with patch.dict(os.environ, {"TRUST_X_FORWARDED_FOR": "true"}):
        ip = _get_ip_from_request(request)
        assert ip == "unknown"
    
    # Test invalid client.host
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "not.an.ip"
    ip = _get_ip_from_request(request)
    assert ip == "unknown"


@pytest.mark.asyncio
async def test_check_progressive_ban_no_ban():
    """Test progressive ban check when no ban exists."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test",
        enable_progressive_limits=True
    )
    
    result = await _check_progressive_ban(redis, "192.168.1.1", config)
    assert result is None


@pytest.mark.asyncio
async def test_check_progressive_ban_active_ban():
    """Test progressive ban check when ban is active."""
    redis = AsyncMock()
    now = int(time.time())
    ban_expiry = now + 300  # 5 minutes from now
    redis.get = AsyncMock(return_value=str(ban_expiry))
    
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test",
        enable_progressive_limits=True
    )
    
    result = await _check_progressive_ban(redis, "192.168.1.1", config)
    assert result == ban_expiry


@pytest.mark.asyncio
async def test_check_progressive_ban_expired_ban():
    """Test progressive ban check when ban has expired."""
    redis = AsyncMock()
    now = int(time.time())
    expired_ban = now - 60  # 1 minute ago
    redis.get = AsyncMock(return_value=str(expired_ban))
    redis.delete = AsyncMock()
    
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test",
        enable_progressive_limits=True
    )
    
    result = await _check_progressive_ban(redis, "192.168.1.1", config)
    assert result is None
    redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_apply_progressive_ban_first_violation():
    """Test applying progressive ban for first violation."""
    redis = AsyncMock()
    now = int(time.time())
    expected_ban_expiry = now + 60  # First violation = 60 seconds
    
    # Mock redis.eval() for APPLY_PROGRESSIVE_BAN_LUA
    # Returns: [violation_count, ban_expiry, ban_duration]
    redis.eval = AsyncMock(return_value=[1, expected_ban_expiry, 60])
    
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test",
        enable_progressive_limits=True,
        progressive_ban_durations=[60, 300, 900, 3600]
    )
    
    with patch('backend.rate_limiter.time.time', return_value=now):
        ban_expiry = await _apply_progressive_ban(redis, "192.168.1.1", config)
    
    # First violation should be 60 seconds
    assert ban_expiry == expected_ban_expiry
    redis.eval.assert_called_once()


@pytest.mark.asyncio
async def test_apply_progressive_ban_second_violation():
    """Test applying progressive ban for second violation."""
    redis = AsyncMock()
    now = int(time.time())
    expected_ban_expiry = now + 300  # Second violation = 300 seconds
    
    # Mock redis.eval() for APPLY_PROGRESSIVE_BAN_LUA
    # Returns: [violation_count, ban_expiry, ban_duration]
    redis.eval = AsyncMock(return_value=[2, expected_ban_expiry, 300])
    
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test",
        enable_progressive_limits=True,
        progressive_ban_durations=[60, 300, 900, 3600]
    )
    
    with patch('backend.rate_limiter.time.time', return_value=now):
        ban_expiry = await _apply_progressive_ban(redis, "192.168.1.1", config)
    
    # Second violation should be 300 seconds (5 minutes)
    assert ban_expiry == expected_ban_expiry
    redis.eval.assert_called_once()


@pytest.mark.asyncio
async def test_check_sliding_window_allowed():
    """Test sliding window check when request is allowed (under limit)."""
    redis = AsyncMock()
    # Mock Lua script return: {1, count, oldest_ts} = Allowed
    # For allowed requests, oldest_ts is 0
    redis.eval = AsyncMock(return_value=[1, 5, 0])  # allowed=1, count=5, oldest_ts=0
    
    now = int(time.time())
    count, allowed, retry_after = await _check_sliding_window(
        redis, "test:key", 60, 10, now  # limit=10, count=5 < limit
    )
    
    assert count == 5
    assert allowed is True
    assert retry_after == 0
    redis.eval.assert_called_once()


@pytest.mark.asyncio
async def test_check_sliding_window_rejected():
    """Test sliding window check when request is rejected (over limit)."""
    redis = AsyncMock()
    now = int(time.time())
    oldest_timestamp = now - 30  # 30 seconds ago
    
    # Mock Lua script return: {0, count, oldest_timestamp} = Rejected
    # New format includes oldest_timestamp to avoid extra round-trip
    redis.eval = AsyncMock(return_value=[0, 10, oldest_timestamp])  # allowed=0, count=10, oldest_ts
    
    count, allowed, retry_after = await _check_sliding_window(
        redis, "test:key", 60, 10, now  # limit=10, count=10 >= limit
    )
    
    assert count == 10
    assert allowed is False
    assert retry_after == 30  # 60 - (now - oldest_timestamp) = 60 - 30 = 30
    redis.eval.assert_called_once()
    # No zrange call needed anymore - oldest timestamp comes from Lua script


@pytest.mark.asyncio
async def test_check_sliding_window_deduplication():
    """Test sliding window check with deduplication (duplicate request)."""
    redis = AsyncMock()
    # Mock Lua script return: {1, count, oldest_ts} = Allowed (duplicate)
    # For allowed requests (including duplicates), oldest_ts is 0
    redis.eval = AsyncMock(return_value=[1, 5, 0])  # allowed=1, count=5 (unchanged), oldest_ts=0
    
    now = int(time.time())
    count, allowed, retry_after = await _check_sliding_window(
        redis, "test:key", 60, 10, now, deduplication_id="fp:challenge123:hash456"
    )
    
    assert count == 5
    assert allowed is True
    assert retry_after == 0
    redis.eval.assert_called_once()


@pytest.mark.asyncio
async def test_check_sliding_window_error_handling():
    """Test sliding window check error handling (fail-open strategy)."""
    redis = AsyncMock()
    # Mock Lua script to raise an exception
    redis.eval = AsyncMock(side_effect=Exception("Redis error"))
    
    now = int(time.time())
    count, allowed, retry_after = await _check_sliding_window(
        redis, "test:key", 60, 10, now
    )
    
    # Fail-open: should allow request on error
    assert count == 1
    assert allowed is True
    assert retry_after == 0
    redis.eval.assert_called_once()


if __name__ == "__main__":
    print("Running rate limiter tests...")
    print("\nNote: These are unit tests. For integration tests with Redis,")
    print("run: pytest backend/tests/test_rate_limiter.py -v")
    print("\nBasic configuration tests:")
    
    try:
        test_rate_limit_config_defaults()
        print("✅ RateLimitConfig defaults test passed")
        
        test_rate_limit_config_custom_progressive()
        print("✅ RateLimitConfig custom progressive test passed")
        
        test_get_ip_from_request_cloudflare()
        print("✅ Cloudflare IP extraction test passed")
        
        test_get_ip_from_request_x_forwarded_for()
        print("✅ X-Forwarded-For IP extraction test passed (with trust check)")
        
        test_get_ip_from_request_direct()
        print("✅ Direct IP extraction test passed")
        
        print("\n✅ All basic tests passed!")
        print("\nFor async tests, run with pytest:")
        print("  pytest backend/tests/test_rate_limiter.py -v")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

