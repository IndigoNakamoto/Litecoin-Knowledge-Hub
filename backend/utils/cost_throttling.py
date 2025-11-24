"""
Cost-based throttling utility.

This module provides cost-based throttling to prevent abuse by tracking spending
per fingerprint in a sliding window. If a fingerprint exceeds a spending threshold
within the window, requests are throttled.
"""

import os
import time
import logging
from typing import Optional, Tuple

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Environment variables (will be read dynamically from Redis/env)
# These are defaults, actual values are read in check_cost_based_throttling()


async def check_cost_based_throttling(
    fingerprint: str,
    estimated_cost: float
) -> Tuple[bool, Optional[str]]:
    """
    Check if a fingerprint should be throttled based on recent spending.
    
    Args:
        fingerprint: Client fingerprint (from X-Fingerprint header)
        estimated_cost: Estimated cost in USD for the current request
    
    Returns:
        Tuple of (is_throttled: bool, throttle_reason: Optional[str])
        - is_throttled: True if fingerprint should be throttled, False otherwise
        - throttle_reason: Reason for throttling if throttled, None otherwise
    """
    # Read settings from Redis with env fallback
    from backend.utils.settings_reader import get_setting_from_redis_or_env
    
    redis = await get_redis_client()
    
    enable_cost_throttling = await get_setting_from_redis_or_env(
        redis, "enable_cost_throttling", "ENABLE_COST_THROTTLING", True, bool
    )
    
    # Disable cost throttling in development mode
    is_dev = os.getenv("ENVIRONMENT", "production").lower() == "development" or os.getenv("DEBUG", "false").lower() == "true"
    if is_dev:
        return False, None
    
    if not enable_cost_throttling:
        return False, None
    
    high_cost_threshold_usd = await get_setting_from_redis_or_env(
        redis, "high_cost_threshold_usd", "HIGH_COST_THRESHOLD_USD", 0.10, float
    )
    high_cost_window_seconds = await get_setting_from_redis_or_env(
        redis, "high_cost_window_seconds", "HIGH_COST_WINDOW_SECONDS", 600, int
    )
    cost_throttle_duration_seconds = await get_setting_from_redis_or_env(
        redis, "cost_throttle_duration_seconds", "COST_THROTTLE_DURATION_SECONDS", 30, int
    )
    
    if not fingerprint or not estimated_cost or estimated_cost <= 0:
        return False, None
    
    redis = await get_redis_client()
    now = int(time.time())
    
    # Check if already throttled (throttle marker exists)
    throttle_marker_key = f"llm:throttle:{fingerprint}"
    throttle_marker = await redis.get(throttle_marker_key)
    
    if throttle_marker:
        # Already throttled - check if throttle period has expired
        throttle_timestamp = int(throttle_marker)
        throttle_expiry = throttle_timestamp + cost_throttle_duration_seconds
        
        if now < throttle_expiry:
            # Still in throttle period
            remaining_seconds = throttle_expiry - now
            logger.warning(
                f"Fingerprint {fingerprint} is throttled. "
                f"Remaining throttle time: {remaining_seconds}s"
            )
            return True, f"High usage detected. Please wait {remaining_seconds} seconds before trying again."
        else:
            # Throttle period expired, remove marker
            await redis.delete(throttle_marker_key)
    
    # Track recent spending per fingerprint in sliding window
    cost_key = f"llm:cost:recent:{fingerprint}"
    
    # Remove expired entries (older than window)
    cutoff = now - high_cost_window_seconds
    await redis.zremrangebyscore(cost_key, 0, cutoff)
    
    # Calculate total cost in window
    # Note: member format is "{timestamp}:{cost}", score is timestamp
    # We need to extract cost from member string, not use the score
    all_costs = await redis.zrange(cost_key, 0, -1, withscores=True)
    total_cost_in_window = 0.0
    for member, _ in all_costs:
        # Member format: "{timestamp}:{cost}"
        try:
            # Handle both bytes and string types from Redis
            if isinstance(member, bytes):
                member_str = member.decode('utf-8')
            else:
                member_str = str(member)
            # Split by colon and get the cost part (last element)
            cost_str = member_str.split(':')[-1]
            total_cost_in_window += float(cost_str)
        except (ValueError, IndexError, AttributeError, TypeError) as e:
            # If parsing fails, skip this entry (shouldn't happen, but be safe)
            logger.warning(f"Failed to parse cost from Redis entry {member}: {e}")
            continue
    
    # Check if adding estimated cost would exceed threshold
    new_total_cost = total_cost_in_window + estimated_cost
    
    if new_total_cost >= high_cost_threshold_usd:
        # Throttle fingerprint
        logger.warning(
            f"Cost-based throttling triggered for fingerprint {fingerprint}. "
            f"Total cost in window: ${total_cost_in_window:.4f}, "
            f"Estimated cost: ${estimated_cost:.4f}, "
            f"Threshold: ${high_cost_threshold_usd:.2f}"
        )
        
        # Set throttle marker
        await redis.setex(throttle_marker_key, cost_throttle_duration_seconds, now)
        
        return True, f"High usage detected. Please complete security verification and try again in {cost_throttle_duration_seconds} seconds."
    
    # Record this request's estimated cost in the sliding window
    # Use timestamp as score and cost as member for accurate tracking
    cost_entry = f"{now}:{estimated_cost}"
    await redis.zadd(cost_key, {cost_entry: now})
    
    # Set TTL on the sorted set (slightly longer than window for cleanup)
    await redis.expire(cost_key, high_cost_window_seconds + 60)
    
    return False, None


async def record_actual_cost(
    fingerprint: str,
    actual_cost: float
) -> None:
    """
    Record actual cost for a fingerprint (update sliding window with actual cost).
    
    This can be called after the actual LLM call completes to update the
    cost tracking with the real cost instead of the estimated cost.
    
    Args:
        fingerprint: Client fingerprint (from X-Fingerprint header)
        actual_cost: Actual cost in USD for the completed request
    """
    # Read settings from Redis with env fallback
    from backend.utils.settings_reader import get_setting_from_redis_or_env
    
    redis = await get_redis_client()
    
    enable_cost_throttling = await get_setting_from_redis_or_env(
        redis, "enable_cost_throttling", "ENABLE_COST_THROTTLING", True, bool
    )
    
    if not enable_cost_throttling or not fingerprint or not actual_cost or actual_cost <= 0:
        return
    
    high_cost_window_seconds = await get_setting_from_redis_or_env(
        redis, "high_cost_window_seconds", "HIGH_COST_WINDOW_SECONDS", 600, int
    )
    
    now = int(time.time())
    
    # Record actual cost in sliding window
    cost_key = f"llm:cost:recent:{fingerprint}"
    cost_entry = f"{now}:{actual_cost}"
    await redis.zadd(cost_key, {cost_entry: now})
    
    # Set TTL on the sorted set
    await redis.expire(cost_key, high_cost_window_seconds + 60)

