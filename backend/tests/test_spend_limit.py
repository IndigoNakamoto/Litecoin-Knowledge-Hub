"""
Unit tests for LLM spend limit monitoring module.
"""

import os
import sys
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(backend_dir)
sys.path.insert(0, project_root_dir)

from backend.monitoring.spend_limit import (
    check_spend_limit,
    record_spend,
    get_current_usage,
    _get_daily_key,
    _get_hourly_key,
    DEFAULT_DAILY_SPEND_LIMIT_USD,
    DEFAULT_HOURLY_SPEND_LIMIT_USD,
)
from backend.utils.settings_reader import clear_settings_cache


@pytest.fixture(autouse=True)
def clear_cache_before_test():
    """Clear settings cache before each test to prevent cache pollution."""
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = AsyncMock()
    
    # Smart mock for get() that returns None for settings key, "0.0" for cost keys
    async def smart_get(key):
        key_str = str(key)
        if "admin:settings:abuse_prevention" in key_str:
            return None  # No settings in Redis, use defaults
        return "0.0"  # Default for cost keys
    
    mock_client.get = AsyncMock(side_effect=smart_get)
    mock_client.incrbyfloat = AsyncMock(return_value=1.0)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.hget = AsyncMock(return_value="0")
    mock_client.hincrby = AsyncMock(return_value=100)
    mock_client.eval = AsyncMock(return_value=[0, 0.0, 0.0])  # Default for Lua scripts
    return mock_client


@pytest.mark.asyncio
async def test_get_current_usage_empty(mock_redis_client):
    """Test getting current usage when Redis is empty."""
    # Mock settings reader to return defaults
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        with patch("backend.monitoring.spend_limit.get_setting_from_redis_or_env") as mock_get_setting:
            # Mock settings reader to return defaults
            async def mock_get_setting_impl(redis, key, env_var, default, value_type):
                if key == "daily_spend_limit_usd":
                    return DEFAULT_DAILY_SPEND_LIMIT_USD
                elif key == "hourly_spend_limit_usd":
                    return DEFAULT_HOURLY_SPEND_LIMIT_USD
                return default
            mock_get_setting.side_effect = mock_get_setting_impl
            
            usage = await get_current_usage()
            
            assert "daily" in usage
            assert "hourly" in usage
            assert usage["daily"]["cost_usd"] == 0.0
            assert usage["hourly"]["cost_usd"] == 0.0
            # Limits are now read dynamically, but should use defaults when no settings exist
            assert usage["daily"]["limit_usd"] == DEFAULT_DAILY_SPEND_LIMIT_USD
            assert usage["hourly"]["limit_usd"] == DEFAULT_HOURLY_SPEND_LIMIT_USD


@pytest.mark.asyncio
async def test_get_current_usage_with_costs(mock_redis_client):
    """Test getting current usage with existing costs."""
    # Clear settings cache to ensure fresh state
    clear_settings_cache()
    
    async def get_side_effect(key):
        key_str = str(key)
        # Handle settings key (returns None to use defaults)
        if "admin:settings:abuse_prevention" in key_str:
            return None
        # Return cost values for cost keys based on key content
        if "llm:cost:daily" in key_str:
            return "4.5"
        elif "llm:cost:hourly" in key_str:
            return "0.8"
        return "0.0"
    
    mock_redis_client.get = AsyncMock(side_effect=get_side_effect)
    mock_redis_client.hget = AsyncMock(side_effect=["100000", "50000", "10000", "5000"])
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        usage = await get_current_usage()
        
        assert usage["daily"]["cost_usd"] == 4.5
        assert usage["hourly"]["cost_usd"] == 0.8
        assert usage["daily"]["input_tokens"] == 100000
        assert usage["daily"]["output_tokens"] == 50000
        assert usage["hourly"]["input_tokens"] == 10000
        assert usage["hourly"]["output_tokens"] == 5000


@pytest.mark.asyncio
async def test_check_spend_limit_allows_request_below_limit(mock_redis_client):
    """Test that requests below the limit are allowed."""
    # Mock redis.eval() for CHECK_AND_RESERVE_SPEND_LUA
    # Returns: [status_code, daily_cost, hourly_cost]
    # status_code: 0=allowed (cost was reserved)
    buffered_cost = 0.4 * 1.1  # 0.44
    mock_redis_client.eval = AsyncMock(return_value=[0, 0.5 + buffered_cost, 0.5 + buffered_cost])
    mock_redis_client.hget = AsyncMock(return_value="0")  # Token counts default to 0
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        allowed, error_msg, usage_info = await check_spend_limit(0.4, "test-model")
        
        assert allowed is True
        assert error_msg is None
        assert "daily" in usage_info


@pytest.mark.asyncio
async def test_check_spend_limit_blocks_request_above_daily_limit(mock_redis_client):
    """Test that requests exceeding daily limit are blocked."""
    # Set daily cost close to limit
    daily_cost = DEFAULT_DAILY_SPEND_LIMIT_USD - 0.5  # 4.5
    
    # Mock redis.eval() to simulate Lua script response for daily limit exceeded
    # CHECK_AND_RESERVE_SPEND_LUA returns: [status_code, daily_cost, hourly_cost]
    # status_code: 0=allowed, 1=daily_limit_exceeded, 2=hourly_limit_exceeded
    mock_redis_client.eval = AsyncMock(return_value=[1, daily_cost, 0.0])  # Daily limit exceeded
    mock_redis_client.hget = AsyncMock(return_value="0")  # Token counts default to 0
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        # Request that would exceed limit (with 10% buffer)
        # 4.5 + 0.6*1.1 = 5.16 > 5.0 → blocked
        allowed, error_msg, usage_info = await check_spend_limit(0.6, "test-model")
        
        assert allowed is False
        assert error_msg is not None
        assert "daily" in error_msg.lower() or "limit" in error_msg.lower()


@pytest.mark.asyncio
async def test_check_spend_limit_blocks_request_above_hourly_limit(mock_redis_client):
    """Test that requests exceeding hourly limit are blocked."""
    # Set hourly cost close to limit
    hourly_cost = DEFAULT_HOURLY_SPEND_LIMIT_USD - 0.1  # 0.9
    
    # Mock redis.eval() to simulate Lua script response for hourly limit exceeded
    # CHECK_AND_RESERVE_SPEND_LUA returns: [status_code, daily_cost, hourly_cost]
    # status_code: 0=allowed, 1=daily_limit_exceeded, 2=hourly_limit_exceeded
    mock_redis_client.eval = AsyncMock(return_value=[2, 0.0, hourly_cost])  # Hourly limit exceeded
    mock_redis_client.hget = AsyncMock(return_value="0")  # Token counts default to 0
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        # Request that would exceed limit (with 10% buffer)
        # 0.9 + 0.2*1.1 = 1.12 > 1.0 → blocked
        allowed, error_msg, usage_info = await check_spend_limit(0.2, "test-model")
        
        assert allowed is False
        assert error_msg is not None
        assert "hourly" in error_msg.lower() or "limit" in error_msg.lower()


@pytest.mark.asyncio
async def test_check_spend_limit_allows_zero_cost(mock_redis_client):
    """Test that zero cost requests are always allowed."""
    # Zero cost path calls get_current_usage() which needs get() and hget()
    # The fixture already has smart_get that handles settings key
    mock_redis_client.hget = AsyncMock(return_value="0")
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        allowed, error_msg, usage_info = await check_spend_limit(0.0, "test-model")
        
        assert allowed is True
        assert error_msg is None


@pytest.mark.asyncio
async def test_record_spend_increments_counters(mock_redis_client):
    """Test that recording spend calls the atomic Lua script."""
    # Mock redis.eval() for ADJUST_SPEND_LUA which returns [daily_cost, hourly_cost]
    mock_redis_client.eval = AsyncMock(return_value=[1.5, 1.5])
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        with patch("backend.monitoring.spend_limit.get_current_usage", new_callable=AsyncMock) as mock_usage:
            mock_usage.return_value = {
                "daily": {"cost_usd": 1.5, "limit_usd": 5.0, "remaining_usd": 3.5, "percentage_used": 30.0, "input_tokens": 1000, "output_tokens": 500},
                "hourly": {"cost_usd": 1.5, "limit_usd": 1.0, "remaining_usd": 0.0, "percentage_used": 150.0, "input_tokens": 1000, "output_tokens": 500},
            }
            
            result = await record_spend(0.5, 1000, 500, "test-model")
            
            # Verify the atomic Lua script was called
            assert mock_redis_client.eval.call_count == 1
            # Verify the result contains usage info
            assert "daily" in result
            assert "hourly" in result


@pytest.mark.asyncio
async def test_record_spend_handles_zero_cost(mock_redis_client):
    """Test that zero cost with zero tokens skips Redis operations."""
    mock_redis_client.eval = AsyncMock()
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        with patch("backend.monitoring.spend_limit.get_current_usage", new_callable=AsyncMock) as mock_usage:
            mock_usage.return_value = {
                "daily": {"cost_usd": 0.0, "limit_usd": 5.0, "remaining_usd": 5.0, "percentage_used": 0.0, "input_tokens": 0, "output_tokens": 0},
                "hourly": {"cost_usd": 0.0, "limit_usd": 1.0, "remaining_usd": 1.0, "percentage_used": 0.0, "input_tokens": 0, "output_tokens": 0},
            }
            
            result = await record_spend(0.0, 0, 0, "test-model")
            
            # Verify no Redis eval was called for zero adjustment and zero tokens
            mock_redis_client.eval.assert_not_called()


def test_get_daily_key_format():
    """Test that daily key has correct format."""
    key = _get_daily_key()
    assert key.startswith("llm:cost:daily:")
    # Should be in format YYYY-MM-DD
    date_part = key.split(":")[-1]
    assert len(date_part) == 10
    assert date_part[4] == "-"
    assert date_part[7] == "-"


def test_get_hourly_key_format():
    """Test that hourly key has correct format."""
    key = _get_hourly_key()
    assert key.startswith("llm:cost:hourly:")
    # Should be in format YYYY-MM-DD-HH
    parts = key.split(":")[-1].split("-")
    assert len(parts) == 4
    assert len(parts[0]) == 4  # Year
    assert len(parts[1]) == 2  # Month
    assert len(parts[2]) == 2  # Day
    assert len(parts[3]) == 2  # Hour


@pytest.mark.asyncio
async def test_get_current_usage_handles_redis_error(mock_redis_client):
    """Test that get_current_usage handles Redis errors gracefully."""
    mock_redis_client.get = AsyncMock(side_effect=Exception("Redis error"))
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        usage = await get_current_usage()
        
        # Should return zeros on error (graceful degradation)
        assert usage["daily"]["cost_usd"] == 0.0
        assert usage["hourly"]["cost_usd"] == 0.0


@pytest.mark.asyncio
async def test_check_spend_limit_handles_redis_error(mock_redis_client):
    """Test that check_spend_limit handles Redis errors gracefully."""
    # Make redis.eval() raise an exception to simulate Redis error
    mock_redis_client.eval = AsyncMock(side_effect=Exception("Redis error"))
    # The fixture already has smart_get that handles settings key
    mock_redis_client.hget = AsyncMock(return_value="0")  # For get_current_usage() in error path
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        # Should allow request on error (graceful degradation)
        allowed, error_msg, usage_info = await check_spend_limit(1.0, "test-model")
        
        assert allowed is True  # Graceful degradation allows request


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

