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
from datetime import datetime

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
    # Log entry point for debugging
    logger.info(f"Cost throttling check called: fingerprint={fingerprint[:20] if fingerprint else 'None'}..., estimated_cost=${estimated_cost:.6f}")
    
    # Read settings from Redis with env fallback
    from backend.utils.settings_reader import get_setting_from_redis_or_env
    
    redis = await get_redis_client()
    
    # Check if admin has explicitly set enable_cost_throttling in Redis
    # This allows admin dashboard to control it regardless of dev/prod mode
    from backend.utils.settings_reader import SETTINGS_REDIS_KEY
    import json
    
    admin_explicitly_set = False
    enable_cost_throttling = None
    
    try:
        settings_json = await redis.get(SETTINGS_REDIS_KEY)
        if settings_json:
            settings = json.loads(settings_json)
            logger.info(f"Reading settings from Redis: {list(settings.keys())}")
            if "enable_cost_throttling" in settings:
                admin_explicitly_set = True
                enable_cost_throttling = bool(settings["enable_cost_throttling"])
                logger.info(f"Cost throttling setting from admin dashboard: {enable_cost_throttling} (raw value: {settings['enable_cost_throttling']})")
            else:
                logger.info(f"enable_cost_throttling not found in Redis settings. Available keys: {list(settings.keys())}")
        else:
            logger.info("No settings found in Redis (settings_json is None)")
    except Exception as e:
        logger.error(f"Error reading admin settings from Redis: {e}", exc_info=True)
    
    # If not set by admin, check environment variable
    if not admin_explicitly_set:
        env_value = os.getenv("ENABLE_COST_THROTTLING")
        if env_value is not None:
            enable_cost_throttling = env_value.lower() == "true"
            logger.info(f"Cost throttling setting from environment: {enable_cost_throttling}")
    
    # Check if we're in development mode
    is_dev = os.getenv("ENVIRONMENT", "production").lower() == "development" or os.getenv("DEBUG", "false").lower() == "true"
    
    # Admin dashboard setting takes precedence over dev mode
    if admin_explicitly_set:
        if enable_cost_throttling:
            logger.info(f"Cost throttling ENABLED: admin dashboard setting (works in dev and prod)")
            # Continue to actual throttling logic below
        else:
            logger.info(f"Cost throttling DISABLED: admin dashboard setting")
            return False, None
    else:
        # Not explicitly set by admin - apply default behavior (disabled in dev, enabled in prod)
        if is_dev:
            logger.info(
                f"Cost throttling DISABLED: development mode detected "
                f"(ENVIRONMENT={os.getenv('ENVIRONMENT')}, DEBUG={os.getenv('DEBUG')}). "
                f"Enable via admin dashboard to override."
            )
            return False, None
        # In production, default to enabled if not explicitly set
        logger.info(f"Cost throttling ENABLED: production mode (default behavior)")
        enable_cost_throttling = True
    
    high_cost_threshold_usd = await get_setting_from_redis_or_env(
        redis, "high_cost_threshold_usd", "HIGH_COST_THRESHOLD_USD", 0.02, float
    )
    high_cost_window_seconds = await get_setting_from_redis_or_env(
        redis, "high_cost_window_seconds", "HIGH_COST_WINDOW_SECONDS", 600, int
    )
    cost_throttle_duration_seconds = await get_setting_from_redis_or_env(
        redis, "cost_throttle_duration_seconds", "COST_THROTTLE_DURATION_SECONDS", 30, int
    )
    daily_cost_limit_usd = await get_setting_from_redis_or_env(
        redis, "daily_cost_limit_usd", "DAILY_COST_LIMIT_USD", 0.25, float
    )
    
    # Validate settings
    if high_cost_threshold_usd is None or high_cost_threshold_usd <= 0:
        logger.warning(f"Invalid high_cost_threshold_usd: {high_cost_threshold_usd}, using default 0.02")
        high_cost_threshold_usd = 0.02
    
    if high_cost_window_seconds is None or high_cost_window_seconds <= 0:
        logger.warning(f"Invalid high_cost_window_seconds: {high_cost_window_seconds}, using default 600")
        high_cost_window_seconds = 600
    
    if cost_throttle_duration_seconds is None or cost_throttle_duration_seconds <= 0:
        logger.warning(f"Invalid cost_throttle_duration_seconds: {cost_throttle_duration_seconds}, using default 30")
        cost_throttle_duration_seconds = 30
    
    if daily_cost_limit_usd is None or daily_cost_limit_usd <= 0:
        logger.warning(f"Invalid daily_cost_limit_usd: {daily_cost_limit_usd}, using default 0.25")
        daily_cost_limit_usd = 0.25
    
    # Log settings for debugging
    logger.info(
        f"Cost throttling settings: threshold=${high_cost_threshold_usd:.6f}, "
        f"window={high_cost_window_seconds}s, throttle_duration={cost_throttle_duration_seconds}s, "
        f"daily_limit=${daily_cost_limit_usd:.6f}"
    )
    
    if not fingerprint or not estimated_cost or estimated_cost <= 0:
        logger.info(f"Cost throttling skipped: fingerprint={bool(fingerprint)}, estimated_cost={estimated_cost}")
        return False, None
    
    redis = await get_redis_client()
    now = int(time.time())
    
    # FIX: Extract stable identifier from fingerprint
    # Format: "fp:challenge:hash" or just "hash"
    # We want the stable_hash to group costs together across different challenges.
    # This prevents users from bypassing cost limits by getting new challenges.
    # Note: Only split if it looks like a fingerprint (starts with "fp:")
    # This prevents breaking IPv6 addresses which also contain colons (though cost throttler
    # typically returns early if fingerprint is missing, so IP addresses are rarely processed here)
    if fingerprint.startswith("fp:"):
        # Format: "fp:challenge:hash" - extract the stable hash (last part)
        stable_identifier = fingerprint.split(':')[-1]
    else:
        # Fallback for simple formats (just hash)
        stable_identifier = fingerprint
    
    # KEY (The Bucket): Uses stable_identifier so costs accumulate across challenges
    cost_key = f"llm:cost:recent:{stable_identifier}"
    daily_cost_key = f"llm:cost:daily:{stable_identifier}"
    throttle_marker_key = f"llm:throttle:{stable_identifier}"
    
    # Get current date for daily tracking (YYYY-MM-DD format)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    daily_cost_key_with_date = f"{daily_cost_key}:{today}"
    
    # MEMBER (The Receipt): Uses full fingerprint so we don't double-count THIS specific request
    # This matches the deduplication logic - same challenge = same member = idempotent
    unique_request_member = f"{fingerprint}:{estimated_cost}"
    
    # Check if already throttled (throttle marker exists)
    throttle_marker = await redis.get(throttle_marker_key)
    
    if throttle_marker:
        # Already throttled - check if throttle period has expired
        try:
            throttle_timestamp = int(throttle_marker)
            throttle_expiry = throttle_timestamp + cost_throttle_duration_seconds
            
            if now < throttle_expiry:
                # Still in throttle period
                remaining_seconds = throttle_expiry - now
                logger.warning(
                    f"Fingerprint {fingerprint} (stable_identifier: {stable_identifier}) is throttled. "
                    f"Remaining throttle time: {remaining_seconds}s"
                )
                return True, f"High usage detected. Please wait {remaining_seconds} seconds before trying again."
            else:
                # Throttle period expired, remove marker
                logger.debug(f"Throttle period expired for stable_identifier {stable_identifier}, removing marker")
                await redis.delete(throttle_marker_key)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid throttle marker value for {stable_identifier}: {throttle_marker}, removing it. Error: {e}")
            await redis.delete(throttle_marker_key)
    
    # Remove expired entries (older than window)
    cutoff = now - high_cost_window_seconds
    await redis.zremrangebyscore(cost_key, 0, cutoff)
    
    # Calculate total cost in window
    # Note: member format is "{fingerprint}:{cost}", score is timestamp
    # We sum them all up, regardless of which challenge they used
    all_costs = await redis.zrange(cost_key, 0, -1, withscores=True)
    total_cost_in_window = 0.0
    parsed_count = 0
    failed_count = 0
    
    for member, score in all_costs:
        # Member format: "fp:challenge:hash:cost" or "hash:cost"
        try:
            # Handle both bytes and string types from Redis
            if isinstance(member, bytes):
                member_str = member.decode('utf-8')
            else:
                member_str = str(member)
            # Split by colon and take the last part to be safe against colons in fingerprints
            # Using split(':')[-1] ensures we always get the cost, even if fingerprint contains colons
            cost_str = member_str.split(':')[-1]
            cost_value = float(cost_str)
            total_cost_in_window += cost_value
            parsed_count += 1
        except (ValueError, IndexError, AttributeError, TypeError) as e:
            # If parsing fails, skip this entry (shouldn't happen, but be safe)
            failed_count += 1
            logger.warning(f"Failed to parse cost from Redis entry {member} (score: {score}): {e}")
            continue
    
    logger.info(
        f"Cost window calculation for stable_identifier {stable_identifier[:20] if stable_identifier else 'None'}...: "
        f"{parsed_count} entries parsed, {failed_count} failed, "
        f"total_cost_in_window=${total_cost_in_window:.6f}"
    )
    
    # Check daily limit first (hard cap)
    daily_cost_entries = await redis.zrange(daily_cost_key_with_date, 0, -1, withscores=True)
    total_daily_cost = 0.0
    for member, _ in daily_cost_entries:
        try:
            if isinstance(member, bytes):
                member_str = member.decode('utf-8')
            else:
                member_str = str(member)
            cost_str = member_str.split(':')[-1]
            total_daily_cost += float(cost_str)
        except (ValueError, IndexError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to parse cost from daily Redis entry {member}: {e}")
            continue
    
    new_daily_cost = total_daily_cost + estimated_cost
    
    if new_daily_cost >= daily_cost_limit_usd:
        # Daily limit exceeded - hard throttle
        logger.warning(
            f"Daily cost limit exceeded for stable_identifier {stable_identifier} (fingerprint: {fingerprint}). "
            f"Total daily cost: ${total_daily_cost:.4f}, "
            f"Estimated cost: ${estimated_cost:.4f}, "
            f"Daily limit: ${daily_cost_limit_usd:.2f}"
        )
        
        # Set throttle marker (longer duration for daily limit violation)
        await redis.setex(throttle_marker_key, cost_throttle_duration_seconds * 2, now)
        
        return True, f"Daily usage limit reached. Please try again tomorrow."
    
    # Check if adding estimated cost would exceed 10-minute threshold
    new_total_cost = total_cost_in_window + estimated_cost
    
    # Info logging to track threshold checks (always visible)
    logger.info(
        f"Cost throttling check for stable_identifier {stable_identifier[:20] if stable_identifier else 'None'}...: "
        f"Total cost in window: ${total_cost_in_window:.6f}, "
        f"Estimated cost: ${estimated_cost:.6f}, "
        f"New total cost: ${new_total_cost:.6f}, "
        f"Threshold: ${high_cost_threshold_usd:.6f}"
    )
    
    if new_total_cost >= high_cost_threshold_usd:
        # Throttle fingerprint (10-minute window exceeded)
        logger.warning(
            f"Cost-based throttling triggered for stable_identifier {stable_identifier} (fingerprint: {fingerprint}). "
            f"Total cost in window: ${total_cost_in_window:.4f}, "
            f"Estimated cost: ${estimated_cost:.4f}, "
            f"New total cost: ${new_total_cost:.4f}, "
            f"Threshold: ${high_cost_threshold_usd:.2f}"
        )
        
        # Set throttle marker
        await redis.setex(throttle_marker_key, cost_throttle_duration_seconds, now)
        
        return True, f"High usage detected. Please complete security verification and try again in {cost_throttle_duration_seconds} seconds."
    
    # Record this request's estimated cost in the sliding window
    # FIX: Use full fingerprint as member (for deduplication) in stable bucket (for aggregation)
    # The full fingerprint ensures double-clicks with same challenge are deduplicated
    # The stable_identifier in the key ensures costs accumulate across different challenges
    await redis.zadd(cost_key, {unique_request_member: now})
    
    # Set TTL on the sorted set (slightly longer than window for cleanup)
    await redis.expire(cost_key, high_cost_window_seconds + 60)
    
    # Also record in daily tracking
    await redis.zadd(daily_cost_key_with_date, {unique_request_member: now})
    # Set TTL to 2 days (ensures cleanup even if date changes during request)
    await redis.expire(daily_cost_key_with_date, 172800)
    
    logger.info(
        f"Cost recorded for stable_identifier {stable_identifier[:20] if stable_identifier else 'None'}...: "
        f"${estimated_cost:.6f} added to window (new total: ${new_total_cost:.6f})"
    )
    
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
    
    # FIX: Extract stable identifier from fingerprint (same logic as check_cost_based_throttling)
    # Format: "fp:challenge:hash" or just "hash"
    # Only split if it looks like a fingerprint (starts with "fp:")
    # This prevents breaking IPv6 addresses which also contain colons
    if fingerprint.startswith("fp:"):
        # Format: "fp:challenge:hash" - extract the stable hash (last part)
        stable_identifier = fingerprint.split(':')[-1]
    else:
        # Fallback for simple formats (just hash)
        stable_identifier = fingerprint
    
    # KEY (The Bucket): Uses stable_identifier so costs accumulate across challenges
    cost_key = f"llm:cost:recent:{stable_identifier}"
    daily_cost_key = f"llm:cost:daily:{stable_identifier}"
    
    # Get current date for daily tracking
    today = datetime.utcnow().strftime("%Y-%m-%d")
    daily_cost_key_with_date = f"{daily_cost_key}:{today}"
    
    # MEMBER (The Receipt): Uses full fingerprint so we don't double-count THIS specific request
    unique_request_member = f"{fingerprint}:{actual_cost}"
    
    # Record actual cost in sliding window
    await redis.zadd(cost_key, {unique_request_member: now})
    
    # Set TTL on the sorted set
    await redis.expire(cost_key, high_cost_window_seconds + 60)
    
    # Also record in daily tracking
    await redis.zadd(daily_cost_key_with_date, {unique_request_member: now})
    # Set TTL to 2 days (ensures cleanup even if date changes during request)
    await redis.expire(daily_cost_key_with_date, 172800)

