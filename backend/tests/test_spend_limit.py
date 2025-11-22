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
    DAILY_SPEND_LIMIT_USD,
    HOURLY_SPEND_LIMIT_USD,
)


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value="0.0")
    mock_client.incrbyfloat = AsyncMock(return_value=1.0)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.hget = AsyncMock(return_value="0")
    mock_client.hincrby = AsyncMock(return_value=100)
    return mock_client


@pytest.mark.asyncio
async def test_get_current_usage_empty(mock_redis_client):
    """Test getting current usage when Redis is empty."""
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        usage = await get_current_usage()
        
        assert "daily" in usage
        assert "hourly" in usage
        assert usage["daily"]["cost_usd"] == 0.0
        assert usage["hourly"]["cost_usd"] == 0.0
        assert usage["daily"]["limit_usd"] == DAILY_SPEND_LIMIT_USD
        assert usage["hourly"]["limit_usd"] == HOURLY_SPEND_LIMIT_USD


@pytest.mark.asyncio
async def test_get_current_usage_with_costs(mock_redis_client):
    """Test getting current usage with existing costs."""
    mock_redis_client.get = AsyncMock(side_effect=["4.5", "0.8"])
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
    # Use return_value so it works for all calls (check_spend_limit + get_current_usage)
    mock_redis_client.get = AsyncMock(return_value="0.5")  # Always return low value
    mock_redis_client.hget = AsyncMock(return_value="0")  # Token counts default to 0
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        allowed, error_msg, usage_info = await check_spend_limit(0.4, "test-model")
        
        assert allowed is True
        assert error_msg is None
        assert "daily" in usage_info


@pytest.mark.asyncio
async def test_check_spend_limit_blocks_request_above_daily_limit(mock_redis_client):
    """Test that requests exceeding daily limit are blocked."""
    # Set daily cost close to limit - use side_effect to return different values for hourly vs daily
    daily_cost = DAILY_SPEND_LIMIT_USD - 0.5  # 4.5
    async def get_side_effect(key):
        # Return daily cost for daily key, low value for hourly key
        if "daily" in str(key):
            return str(daily_cost)
        else:
            return "0.0"  # Hourly is low, so daily limit is checked first
    
    mock_redis_client.get = AsyncMock(side_effect=get_side_effect)
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
    # Set hourly cost close to limit - use a function to return different values based on key
    hourly_cost = HOURLY_SPEND_LIMIT_USD - 0.1  # 0.9
    async def get_side_effect(key):
        # Return hourly cost for hourly key, 0.0 for daily key
        if "hourly" in str(key):
            return str(hourly_cost)
        else:
            return "0.0"
    
    mock_redis_client.get = AsyncMock(side_effect=get_side_effect)
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
    mock_redis_client.get = AsyncMock(return_value="0.0")
    mock_redis_client.hget = AsyncMock(return_value="0")
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        allowed, error_msg, usage_info = await check_spend_limit(0.0, "test-model")
        
        assert allowed is True
        assert error_msg is None


@pytest.mark.asyncio
async def test_record_spend_increments_counters(mock_redis_client):
    """Test that recording spend increments Redis counters."""
    mock_redis_client.incrbyfloat = AsyncMock(return_value=1.5)
    mock_redis_client.hincrby = AsyncMock(return_value=1000)
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        with patch("backend.monitoring.spend_limit.get_current_usage", new_callable=AsyncMock) as mock_usage:
            mock_usage.return_value = {
                "daily": {"cost_usd": 1.5, "limit_usd": 5.0, "remaining_usd": 3.5, "percentage_used": 30.0, "input_tokens": 1000, "output_tokens": 500},
                "hourly": {"cost_usd": 1.5, "limit_usd": 1.0, "remaining_usd": 0.0, "percentage_used": 150.0, "input_tokens": 1000, "output_tokens": 500},
            }
            
            result = await record_spend(0.5, 1000, 500, "test-model")
            
            # Verify Redis operations were called
            assert mock_redis_client.incrbyfloat.call_count >= 2  # Daily and hourly
            assert mock_redis_client.hincrby.call_count >= 2  # Input and output tokens
            assert mock_redis_client.expire.call_count >= 4  # TTLs for all keys


@pytest.mark.asyncio
async def test_record_spend_handles_zero_cost(mock_redis_client):
    """Test that zero cost is not recorded."""
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        with patch("backend.monitoring.spend_limit.get_current_usage", new_callable=AsyncMock) as mock_usage:
            mock_usage.return_value = {
                "daily": {"cost_usd": 0.0, "limit_usd": 5.0, "remaining_usd": 5.0, "percentage_used": 0.0, "input_tokens": 0, "output_tokens": 0},
                "hourly": {"cost_usd": 0.0, "limit_usd": 1.0, "remaining_usd": 1.0, "percentage_used": 0.0, "input_tokens": 0, "output_tokens": 0},
            }
            
            result = await record_spend(0.0, 0, 0, "test-model")
            
            # Verify no Redis operations were called for zero cost
            mock_redis_client.incrbyfloat.assert_not_called()


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
    # First call to get() raises, but get_current_usage() in except block also needs mocks
    mock_redis_client.get = AsyncMock(side_effect=Exception("Redis error"))
    mock_redis_client.hget = AsyncMock(return_value="0")  # For get_current_usage() in error path
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        # Should allow request on error (graceful degradation)
        allowed, error_msg, usage_info = await check_spend_limit(1.0, "test-model")
        
        assert allowed is True  # Graceful degradation allows request


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

