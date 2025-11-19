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

logger = logging.getLogger(__name__)

# Environment variables
DAILY_SPEND_LIMIT_USD = float(os.getenv("DAILY_SPEND_LIMIT_USD", "5.00"))
HOURLY_SPEND_LIMIT_USD = float(os.getenv("HOURLY_SPEND_LIMIT_USD", "1.00"))

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
    redis_client = get_redis_client()
    
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
        daily_percentage = (daily_cost / DAILY_SPEND_LIMIT_USD * 100) if DAILY_SPEND_LIMIT_USD > 0 else 0.0
        hourly_percentage = (hourly_cost / HOURLY_SPEND_LIMIT_USD * 100) if HOURLY_SPEND_LIMIT_USD > 0 else 0.0
        
        daily_remaining = max(0.0, DAILY_SPEND_LIMIT_USD - daily_cost)
        hourly_remaining = max(0.0, HOURLY_SPEND_LIMIT_USD - hourly_cost)
        
        return {
            "daily": {
                "cost_usd": round(daily_cost, 4),
                "limit_usd": DAILY_SPEND_LIMIT_USD,
                "remaining_usd": round(daily_remaining, 4),
                "percentage_used": round(daily_percentage, 2),
                "input_tokens": daily_input_tokens,
                "output_tokens": daily_output_tokens,
            },
            "hourly": {
                "cost_usd": round(hourly_cost, 4),
                "limit_usd": HOURLY_SPEND_LIMIT_USD,
                "remaining_usd": round(hourly_remaining, 4),
                "percentage_used": round(hourly_percentage, 2),
                "input_tokens": hourly_input_tokens,
                "output_tokens": hourly_output_tokens,
            },
        }
    except Exception as e:
        logger.error(f"Error getting current usage from Redis: {e}", exc_info=True)
        # Return zeros on error (graceful degradation)
        return {
            "daily": {
                "cost_usd": 0.0,
                "limit_usd": DAILY_SPEND_LIMIT_USD,
                "remaining_usd": DAILY_SPEND_LIMIT_USD,
                "percentage_used": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
            },
            "hourly": {
                "cost_usd": 0.0,
                "limit_usd": HOURLY_SPEND_LIMIT_USD,
                "remaining_usd": HOURLY_SPEND_LIMIT_USD,
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
    Pre-flight check to determine if a request would exceed spend limits.
    
    Args:
        estimated_cost: Estimated cost in USD for the request
        model: LLM model name (for logging)
    
    Returns:
        Tuple of (allowed: bool, error_message: Optional[str], usage_info: dict)
        - allowed: True if request is allowed, False if it would exceed limits
        - error_message: Error message if not allowed, None otherwise
        - usage_info: Current usage information
    """
    if estimated_cost <= 0:
        # No cost, always allow
        usage_info = await get_current_usage()
        return True, None, usage_info
    
    # Add 10% buffer for safety
    buffered_cost = estimated_cost * 1.1
    
    redis_client = get_redis_client()
    daily_key = _get_daily_key()
    hourly_key = _get_hourly_key()
    
    try:
        # Get current costs (default to 0.0 if key doesn't exist)
        daily_cost = float(await redis_client.get(daily_key) or "0.0")
        hourly_cost = float(await redis_client.get(hourly_key) or "0.0")
        
        # Check if adding buffered cost would exceed limits
        new_daily_cost = daily_cost + buffered_cost
        new_hourly_cost = hourly_cost + buffered_cost
        
        # Check daily limit
        if new_daily_cost > DAILY_SPEND_LIMIT_USD:
            usage_info = await get_current_usage()
            error_msg = (
                f"Daily LLM spend limit would be exceeded. "
                f"Current: ${daily_cost:.4f}, Request: ${buffered_cost:.4f}, "
                f"Limit: ${DAILY_SPEND_LIMIT_USD:.2f}"
            )
            logger.warning(f"Spend limit check failed (daily): {error_msg}")
            return False, error_msg, usage_info
        
        # Check hourly limit
        if new_hourly_cost > HOURLY_SPEND_LIMIT_USD:
            usage_info = await get_current_usage()
            error_msg = (
                f"Hourly LLM spend limit would be exceeded. "
                f"Current: ${hourly_cost:.4f}, Request: ${buffered_cost:.4f}, "
                f"Limit: ${HOURLY_SPEND_LIMIT_USD:.2f}"
            )
            logger.warning(f"Spend limit check failed (hourly): {error_msg}")
            return False, error_msg, usage_info
        
        # Request is allowed
        usage_info = await get_current_usage()
        return True, None, usage_info
        
    except Exception as e:
        logger.error(f"Error checking spend limit: {e}", exc_info=True)
        # On error, allow request but log warning (graceful degradation)
        usage_info = await get_current_usage()
        return True, None, usage_info


async def record_spend(
    actual_cost: float,
    input_tokens: int,
    output_tokens: int,
    model: str
) -> Dict[str, Any]:
    """
    Record actual cost and tokens after a successful LLM API call.
    
    Uses atomic Redis operations for thread safety across multiple instances.
    
    Args:
        actual_cost: Actual cost in USD for the request
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
        model: LLM model name (for logging)
    
    Returns:
        Dictionary with updated usage information
    """
    if actual_cost <= 0:
        # No cost to record
        return await get_current_usage()
    
    redis_client = get_redis_client()
    daily_key = _get_daily_key()
    hourly_key = _get_hourly_key()
    daily_token_key = _get_daily_token_key()
    hourly_token_key = _get_hourly_token_key()
    
    try:
        # Atomic increment for costs
        await redis_client.incrbyfloat(daily_key, actual_cost)
        await redis_client.incrbyfloat(hourly_key, actual_cost)
        
        # Set TTLs (only if key was just created, but safe to set every time)
        await redis_client.expire(daily_key, DAILY_KEY_TTL)
        await redis_client.expire(hourly_key, HOURLY_KEY_TTL)
        
        # Atomic increment for token counts
        if input_tokens > 0:
            await redis_client.hincrby(daily_token_key, "input", input_tokens)
            await redis_client.hincrby(hourly_token_key, "input", input_tokens)
            await redis_client.expire(daily_token_key, DAILY_KEY_TTL)
            await redis_client.expire(hourly_token_key, HOURLY_KEY_TTL)
        
        if output_tokens > 0:
            await redis_client.hincrby(daily_token_key, "output", output_tokens)
            await redis_client.hincrby(hourly_token_key, "output", output_tokens)
            await redis_client.expire(daily_token_key, DAILY_KEY_TTL)
            await redis_client.expire(hourly_token_key, HOURLY_KEY_TTL)
        
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

