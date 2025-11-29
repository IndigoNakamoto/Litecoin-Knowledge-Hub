"""
Integration tests for LLM spend limit monitoring.
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(backend_dir)
sys.path.insert(0, project_root_dir)

from backend.monitoring.spend_limit import check_spend_limit, record_spend, get_current_usage
from backend.monitoring.discord_alerts import send_spend_limit_alert
from backend.utils.settings_reader import clear_settings_cache


@pytest.mark.asyncio
async def test_discord_alert_sent_at_80_percent():
    with patch("backend.monitoring.discord_alerts.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Patch the module-level variable (set at import time)
        with patch("backend.monitoring.discord_alerts.DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test"):
            result = await send_spend_limit_alert(
                "daily", current_cost=4.0, limit=5.0, percentage=80.0, is_exceeded=False
            )
            assert result is True


@pytest.mark.asyncio
async def test_discord_alert_sent_at_100_percent():
    """Test that Discord alert is sent at 100% threshold."""
    with patch("backend.monitoring.discord_alerts.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        
        # Patch the module-level variable (set at import time)
        with patch("backend.monitoring.discord_alerts.DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test"):
            result = await send_spend_limit_alert(
                "hourly",
                current_cost=1.0,
                limit=1.0,
                percentage=100.0,
                is_exceeded=True
            )
            
            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "embeds" in call_args[1]["json"]
            assert call_args[1]["json"]["embeds"][0]["title"] == "🚨 LLM Spend Limit EXCEEDED - HOURLY"


@pytest.mark.asyncio
async def test_discord_alert_not_sent_when_webhook_not_configured():
    """Test that Discord alert is not sent when webhook URL is not configured."""
    # Patch the module-level variable to None
    with patch("backend.monitoring.discord_alerts.DISCORD_WEBHOOK_URL", None):
        result = await send_spend_limit_alert(
            "daily",
            current_cost=4.0,
            limit=5.0,
            percentage=80.0,
            is_exceeded=False
        )
        
        assert result is False


@pytest.mark.asyncio
async def test_discord_alert_handles_http_error():
    """Test that Discord alert handles HTTP errors gracefully."""
    with patch("backend.monitoring.discord_alerts.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=Exception("HTTP error"))
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        
        # Patch the module-level variable (set at import time)
        with patch("backend.monitoring.discord_alerts.DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test"):
            result = await send_spend_limit_alert(
                "daily",
                current_cost=4.0,
                limit=5.0,
                percentage=80.0,
                is_exceeded=False
            )
            
            assert result is False  # Should return False on error


@pytest.mark.asyncio
async def test_spend_limit_check_with_10_percent_buffer():
    """Test that spend limit check includes 10% buffer."""
    # Clear settings cache to ensure fresh state
    clear_settings_cache()
    
    mock_redis_client = AsyncMock()
    # Set daily cost to limit - 0.5
    daily_cost = 5.0 - 0.5  # 4.5
    # Use side_effect to return different values for hourly vs daily
    async def get_side_effect(key):
        key_str = str(key)
        # Handle settings key (returns None to use defaults)
        if "admin:settings:abuse_prevention" in key_str:
            return None
        # Return daily cost for daily key, low value for hourly key
        if "daily" in key_str and "llm:cost:daily" in key_str:
            return str(daily_cost)
        elif "hourly" in key_str and "llm:cost:hourly" in key_str:
            return "0.0"  # Hourly is low, so daily limit is checked first
        else:
            return "0.0"  # Default for other keys
    
    mock_redis_client.get = AsyncMock(side_effect=get_side_effect)
    mock_redis_client.hget = AsyncMock(return_value="0")  # Token counts default to 0
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        # Request of 0.4 should be allowed (4.5 + 0.4*1.1 = 4.94 < 5.0)
        allowed, error_msg, _ = await check_spend_limit(0.4, "test-model")
        assert allowed is True
        
        # Request of 0.6 should be blocked (4.5 + 0.6*1.1 = 5.16 > 5.0)
        allowed, error_msg, _ = await check_spend_limit(0.6, "test-model")
        assert allowed is False


@pytest.mark.asyncio
async def test_record_spend_updates_prometheus_metrics():
    """Test that recording spend updates Prometheus metrics."""
    mock_redis_client = AsyncMock()
    mock_redis_client.incrbyfloat = AsyncMock(return_value=1.0)
    mock_redis_client.hincrby = AsyncMock(return_value=1000)
    mock_redis_client.expire = AsyncMock(return_value=True)
    
    with patch("backend.monitoring.spend_limit.get_redis_client", return_value=mock_redis_client):
        with patch("backend.monitoring.spend_limit.get_current_usage", new_callable=AsyncMock) as mock_usage:
            mock_usage.return_value = {
                "daily": {"cost_usd": 1.0, "limit_usd": 5.0, "remaining_usd": 4.0, "percentage_used": 20.0, "input_tokens": 1000, "output_tokens": 500},
                "hourly": {"cost_usd": 1.0, "limit_usd": 1.0, "remaining_usd": 0.0, "percentage_used": 100.0, "input_tokens": 1000, "output_tokens": 500},
            }
            
            with patch("backend.monitoring.metrics.llm_daily_cost_usd") as mock_daily_gauge:
                with patch("backend.monitoring.metrics.llm_hourly_cost_usd") as mock_hourly_gauge:
                    await record_spend(0.5, 1000, 500, "test-model")
                    
                    # Verify Prometheus gauges were updated
                    mock_daily_gauge.set.assert_called_once_with(1.0)
                    mock_hourly_gauge.set.assert_called_once_with(1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

