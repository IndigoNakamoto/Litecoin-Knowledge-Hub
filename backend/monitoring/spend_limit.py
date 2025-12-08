"""
LLM Spend Limit Monitoring Module

This module provides cost control for LLM API usage by tracking daily and hourly
spend limits in Redis, with atomic operations for thread safety across multiple instances.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from backend.redis_client import get_redis_client
from backend.utils.settings_reader import get_setting_from_redis_or_env
from backend.utils.lua_scripts import CHECK_AND_RESERVE_SPEND_LUA, ADJUST_SPEND_LUA

logger = logging.getLogger(__name__)

# Default values (will be read dynamically from Redis/env)
DEFAULT_DAILY_SPEND_LIMIT_USD = 5.00
DEFAULT_HOURLY_SPEND_LIMIT_USD = 1.00

# TTLs for Redis keys (in seconds)
DAILY_KEY_TTL = 48 * 60 * 60  # 48 hours
HOURLY_KEY_TTL = 2 * 60 * 60  # 2 hours


def _get_daily_key() -> str:
    """Get Redis key for daily cost counter (UTC date)."""
    now = datetime.now(timezone.utc)
    return f"llm:cost:daily:{now.strftime('%Y-%m-%d')}"


def _get_hourly_key() -> str:
    """Get Redis key for hourly cost counter (UTC date-hour)."""
    now = datetime.now(timezone.utc)
    return f"llm:cost:hourly:{now.strftime('%Y-%m-%d-%H')}"


def _get_daily_token_key() -> str:
    """Get Redis key for daily token counter (UTC date)."""
    now = datetime.now(timezone.utc)
    return f"llm:tokens:daily:{now.strftime('%Y-%m-%d')}"


def _get_hourly_token_key() -> str:
    """Get Redis key for hourly token counter (UTC date-hour)."""
    now = datetime.now(timezone.utc)
    return f"llm:tokens:hourly:{now.strftime('%Y-%m-%d-%H')}"


async def get_current_usage() -> Dict[str, Any]:
    """
    Get current daily and hourly usage from Redis.
    
    Returns:
        Dictionary with daily and hourly usage info including costs, limits, percentages, and tokens.
    """
    redis_client = await get_redis_client()
    
    # Read limits from Redis with env fallback
    daily_spend_limit_usd = await get_setting_from_redis_or_env(
        redis_client, "daily_spend_limit_usd", "DAILY_SPEND_LIMIT_USD", DEFAULT_DAILY_SPEND_LIMIT_USD, float
    )
    hourly_spend_limit_usd = await get_setting_from_redis_or_env(
        redis_client, "hourly_spend_limit_usd", "HOURLY_SPEND_LIMIT_USD", DEFAULT_HOURLY_SPEND_LIMIT_USD, float
    )
    
    daily_key = _get_daily_key()
    hourly_key = _get_hourly_key()
    daily_token_key = _get_daily_token_key()
    hourly_token_key = _get_hourly_token_key()
    
    try:
        # Get costs (default to 0.0 if key doesn't exist)
        daily_cost = float(await redis_client.get(daily_key) or "0.0")
        hourly_cost = float(await redis_client.get(hourly_key) or "0.0")
        
        # Get token counts (default to 0 if hash doesn't exist)
        daily_input_tokens = int(await redis_client.hget(daily_token_key, "input") or "0")
        daily_output_tokens = int(await redis_client.hget(daily_token_key, "output") or "0")
        hourly_input_tokens = int(await redis_client.hget(hourly_token_key, "input") or "0")
        hourly_output_tokens = int(await redis_client.hget(hourly_token_key, "output") or "0")
        
        # Calculate percentages and remaining
        daily_percentage = (daily_cost / daily_spend_limit_usd * 100) if daily_spend_limit_usd > 0 else 0.0
        hourly_percentage = (hourly_cost / hourly_spend_limit_usd * 100) if hourly_spend_limit_usd > 0 else 0.0
        
        daily_remaining = max(0.0, daily_spend_limit_usd - daily_cost)
        hourly_remaining = max(0.0, hourly_spend_limit_usd - hourly_cost)
        
        return {
            "daily": {
                "cost_usd": round(daily_cost, 4),
                "limit_usd": daily_spend_limit_usd,
                "remaining_usd": round(daily_remaining, 4),
                "percentage_used": round(daily_percentage, 2),
                "input_tokens": daily_input_tokens,
                "output_tokens": daily_output_tokens,
            },
            "hourly": {
                "cost_usd": round(hourly_cost, 4),
                "limit_usd": hourly_spend_limit_usd,
                "remaining_usd": round(hourly_remaining, 4),
                "percentage_used": round(hourly_percentage, 2),
                "input_tokens": hourly_input_tokens,
                "output_tokens": hourly_output_tokens,
            },
        }
    except Exception as e:
        logger.error(f"Error getting current usage from Redis: {e}", exc_info=True)
        # Return zeros on error (graceful degradation)
        # Read limits from Redis with env fallback for error case
        try:
            daily_spend_limit_usd = await get_setting_from_redis_or_env(
                redis_client, "daily_spend_limit_usd", "DAILY_SPEND_LIMIT_USD", DEFAULT_DAILY_SPEND_LIMIT_USD, float
            )
            hourly_spend_limit_usd = await get_setting_from_redis_or_env(
                redis_client, "hourly_spend_limit_usd", "HOURLY_SPEND_LIMIT_USD", DEFAULT_HOURLY_SPEND_LIMIT_USD, float
            )
        except Exception:
            daily_spend_limit_usd = DEFAULT_DAILY_SPEND_LIMIT_USD
            hourly_spend_limit_usd = DEFAULT_HOURLY_SPEND_LIMIT_USD
        
        return {
            "daily": {
                "cost_usd": 0.0,
                "limit_usd": daily_spend_limit_usd,
                "remaining_usd": daily_spend_limit_usd,
                "percentage_used": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
            },
            "hourly": {
                "cost_usd": 0.0,
                "limit_usd": hourly_spend_limit_usd,
                "remaining_usd": hourly_spend_limit_usd,
                "percentage_used": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
            },
        }


async def check_spend_limit(
    estimated_cost: float,
    model: str
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Pre-flight check and reservation to determine if a request would exceed spend limits.
    
    Uses atomic Lua script to check limits AND reserve the buffered cost in a single operation.
    This prevents race conditions where multiple concurrent requests could all pass the check
    before any spend is recorded.
    
    Args:
        estimated_cost: Estimated cost in USD for the request
        model: LLM model name (for logging)
    
    Returns:
        Tuple of (allowed: bool, error_message: Optional[str], usage_info: dict)
        - allowed: True if request is allowed (cost reserved), False if it would exceed limits
        - error_message: Error message if not allowed, None otherwise
        - usage_info: Current usage information with 'reserved_cost' field if allowed
    """
    if estimated_cost <= 0:
        # No cost, always allow
        usage_info = await get_current_usage()
        usage_info['reserved_cost'] = 0.0
        return True, None, usage_info
    
    # Add 10% buffer for safety
    buffered_cost = estimated_cost * 1.1
    
    redis_client = await get_redis_client()
    
    # Read limits from Redis with env fallback
    daily_spend_limit_usd = await get_setting_from_redis_or_env(
        redis_client, "daily_spend_limit_usd", "DAILY_SPEND_LIMIT_USD", DEFAULT_DAILY_SPEND_LIMIT_USD, float
    )
    hourly_spend_limit_usd = await get_setting_from_redis_or_env(
        redis_client, "hourly_spend_limit_usd", "HOURLY_SPEND_LIMIT_USD", DEFAULT_HOURLY_SPEND_LIMIT_USD, float
    )
    
    daily_key = _get_daily_key()
    hourly_key = _get_hourly_key()
    
    try:
        # Use atomic Lua script to check limits and reserve cost
        result = await redis_client.eval(
            CHECK_AND_RESERVE_SPEND_LUA,
            2,  # Number of keys
            daily_key,
            hourly_key,
            buffered_cost,  # ARGV[1]
            daily_spend_limit_usd,  # ARGV[2]
            hourly_spend_limit_usd,  # ARGV[3]
            DAILY_KEY_TTL,  # ARGV[4]
            HOURLY_KEY_TTL,  # ARGV[5]
        )
        
        status_code = result[0]
        daily_cost = float(result[1])
        hourly_cost = float(result[2])
        
        if status_code == 1:
            # Daily limit would be exceeded (cost NOT reserved)
            usage_info = await get_current_usage()
            error_msg = (
                f"Daily LLM spend limit would be exceeded. "
                f"Current: ${daily_cost:.4f}, Request: ${buffered_cost:.4f}, "
                f"Limit: ${daily_spend_limit_usd:.2f}"
            )
            logger.warning(f"Spend limit check failed (daily): {error_msg}")
            return False, error_msg, usage_info
        
        if status_code == 2:
            # Hourly limit would be exceeded (cost NOT reserved)
            usage_info = await get_current_usage()
            error_msg = (
                f"Hourly LLM spend limit would be exceeded. "
                f"Current: ${hourly_cost:.4f}, Request: ${buffered_cost:.4f}, "
                f"Limit: ${hourly_spend_limit_usd:.2f}"
            )
            logger.warning(f"Spend limit check failed (hourly): {error_msg}")
            return False, error_msg, usage_info
        
        # status_code == 0: Request is allowed and cost was reserved atomically
        usage_info = await get_current_usage()
        usage_info['reserved_cost'] = buffered_cost
        return True, None, usage_info
        
    except Exception as e:
        logger.error(f"Error checking spend limit: {e}", exc_info=True)
        # On error, allow request but log warning (graceful degradation)
        usage_info = await get_current_usage()
        usage_info['reserved_cost'] = 0.0
        return True, None, usage_info


async def record_spend(
    actual_cost: float,
    input_tokens: int,
    output_tokens: int,
    model: str,
    reserved_cost: float = 0.0
) -> Dict[str, Any]:
    """
    Finalize spend by adjusting from reserved cost to actual cost and recording tokens.
    
    Uses atomic Lua script to adjust costs and record tokens in a single operation.
    
    Args:
        actual_cost: Actual cost in USD for the request
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
        model: LLM model name (for logging)
        reserved_cost: The cost that was reserved by check_spend_limit() (default: 0.0)
                      If 0.0, the actual_cost is added directly (backward compatible).
                      If > 0, the adjustment (actual_cost - reserved_cost) is applied.
    
    Returns:
        Dictionary with updated usage information
    """
    # Calculate adjustment: if reserved_cost was provided, we adjust by the difference
    # If reserved_cost is 0, we're in backward-compatible mode and just add actual_cost
    if reserved_cost > 0:
        cost_adjustment = actual_cost - reserved_cost
    else:
        cost_adjustment = actual_cost
    
    # Skip if no adjustment and no tokens to record
    if cost_adjustment == 0 and input_tokens <= 0 and output_tokens <= 0:
        return await get_current_usage()
    
    redis_client = await get_redis_client()
    daily_key = _get_daily_key()
    hourly_key = _get_hourly_key()
    daily_token_key = _get_daily_token_key()
    hourly_token_key = _get_hourly_token_key()
    
    try:
        # Use atomic Lua script to adjust costs and record tokens
        result = await redis_client.eval(
            ADJUST_SPEND_LUA,
            4,  # Number of keys
            daily_key,
            hourly_key,
            daily_token_key,
            hourly_token_key,
            cost_adjustment,  # ARGV[1]
            input_tokens,  # ARGV[2]
            output_tokens,  # ARGV[3]
            DAILY_KEY_TTL,  # ARGV[4]
            HOURLY_KEY_TTL,  # ARGV[5]
        )
        
        # Update Prometheus metrics
        try:
            from backend.monitoring.metrics import (
                llm_daily_cost_usd,
                llm_hourly_cost_usd,
            )
            usage_info = await get_current_usage()
            llm_daily_cost_usd.set(usage_info["daily"]["cost_usd"])
            llm_hourly_cost_usd.set(usage_info["hourly"]["cost_usd"])
        except ImportError:
            # Metrics not available, continue without updating
            pass
        
        return await get_current_usage()
        
    except Exception as e:
        logger.error(f"Error recording spend: {e}", exc_info=True)
        # Return current usage even on error
        return await get_current_usage()

