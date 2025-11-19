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
    _get_sliding_window_count,
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
    """Test IP extraction with Cloudflare header."""
    request = MagicMock(spec=Request)
    request.headers = {"CF-Connecting-IP": "192.168.1.100"}
    request.client = None
    
    ip = _get_ip_from_request(request)
    assert ip == "192.168.1.100"


def test_get_ip_from_request_x_forwarded_for():
    """Test IP extraction with X-Forwarded-For header."""
    request = MagicMock(spec=Request)
    request.headers = {"X-Forwarded-For": "192.168.1.200, 10.0.0.1"}
    request.client = None
    
    ip = _get_ip_from_request(request)
    assert ip == "192.168.1.200"


def test_get_ip_from_request_direct():
    """Test IP extraction from direct client connection."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    
    ip = _get_ip_from_request(request)
    assert ip == "127.0.0.1"


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
    redis.incr = AsyncMock(return_value=1)  # First violation
    redis.expire = AsyncMock()
    redis.setex = AsyncMock()
    
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test",
        enable_progressive_limits=True,
        progressive_ban_durations=[60, 300, 900, 3600]
    )
    
    now = int(time.time())
    with patch('backend.rate_limiter.time.time', return_value=now):
        ban_expiry = await _apply_progressive_ban(redis, "192.168.1.1", config)
    
    # First violation should be 60 seconds
    assert ban_expiry == now + 60
    redis.incr.assert_called_once()
    redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_apply_progressive_ban_second_violation():
    """Test applying progressive ban for second violation."""
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=2)  # Second violation
    redis.expire = AsyncMock()
    redis.setex = AsyncMock()
    
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test",
        enable_progressive_limits=True,
        progressive_ban_durations=[60, 300, 900, 3600]
    )
    
    now = int(time.time())
    with patch('backend.rate_limiter.time.time', return_value=now):
        ban_expiry = await _apply_progressive_ban(redis, "192.168.1.1", config)
    
    # Second violation should be 300 seconds (5 minutes)
    assert ban_expiry == now + 300


@pytest.mark.asyncio
async def test_get_sliding_window_count():
    """Test sliding window count calculation."""
    redis = AsyncMock()
    redis.zremrangebyscore = AsyncMock()
    redis.zadd = AsyncMock()
    redis.expire = AsyncMock()
    redis.zcard = AsyncMock(return_value=5)
    
    now = int(time.time())
    count = await _get_sliding_window_count(redis, "test:key", 60, now)
    
    assert count == 5
    redis.zremrangebyscore.assert_called_once()
    redis.zadd.assert_called_once()
    redis.expire.assert_called_once()
    redis.zcard.assert_called_once()


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
        print("✅ X-Forwarded-For IP extraction test passed")
        
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

