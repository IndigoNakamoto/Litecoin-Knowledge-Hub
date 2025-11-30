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
from backend.utils.lua_scripts import COST_THROTTLE_LUA, RECORD_COST_LUA

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
    
    # Calculate daily TTL (2 days = 172800 seconds)
    daily_ttl = 172800
    
    # Use atomic Lua script to check and record cost
    try:
        result = await redis.eval(
            COST_THROTTLE_LUA,
            3,  # Number of keys
            cost_key,
            daily_cost_key_with_date,
            throttle_marker_key,
            now,  # ARGV[1]
            high_cost_window_seconds,  # ARGV[2]
            estimated_cost,  # ARGV[3]
            high_cost_threshold_usd,  # ARGV[4]
            daily_cost_limit_usd,  # ARGV[5]
            cost_throttle_duration_seconds,  # ARGV[6]
            unique_request_member,  # ARGV[7]
            daily_ttl,  # ARGV[8]
        )
        
        # Parse result: [status_code, ttl_or_duration]
        status_code = result[0]
        ttl_or_duration = result[1]
        
        if status_code == 0:
            # Request allowed
            logger.info(
                f"Cost recorded for stable_identifier {stable_identifier[:20] if stable_identifier else 'None'}...: "
                f"${estimated_cost:.6f} added to window"
            )
            return False, None
        elif status_code == 1:
            # Already throttled
            remaining_seconds = ttl_or_duration
            logger.warning(
                f"Fingerprint {fingerprint} (stable_identifier: {stable_identifier}) is throttled. "
                f"Remaining throttle time: {remaining_seconds}s"
            )
            return True, f"High usage detected. Please wait {remaining_seconds} seconds before trying again."
        elif status_code == 2:
            # Daily limit exceeded
            throttle_duration = ttl_or_duration
            logger.warning(
                f"Daily cost limit exceeded for stable_identifier {stable_identifier} (fingerprint: {fingerprint}). "
                f"Estimated cost: ${estimated_cost:.4f}, "
                f"Daily limit: ${daily_cost_limit_usd:.2f}"
            )
            return True, f"Daily usage limit reached. Please try again tomorrow."
        elif status_code == 3:
            # Window threshold exceeded
            throttle_duration = ttl_or_duration
            logger.warning(
                f"Cost-based throttling triggered for stable_identifier {stable_identifier} (fingerprint: {fingerprint}). "
                f"Estimated cost: ${estimated_cost:.4f}, "
                f"Threshold: ${high_cost_threshold_usd:.2f}"
            )
            return True, f"High usage detected. Please complete security verification and try again in {throttle_duration} seconds."
        else:
            # Unknown status code - fail open
            logger.error(
                f"Unknown status code from cost throttle Lua script: {status_code} "
                f"(fingerprint: {fingerprint[:20] if fingerprint else 'None'}...)"
            )
            return False, None
            
    except Exception as e:
        # Fail-open strategy: log error and allow request to proceed
        logger.error(
            f"Error executing cost throttle Lua script for fingerprint {fingerprint[:20] if fingerprint else 'None'}... "
            f"(stable_identifier: {stable_identifier[:20] if stable_identifier else 'None'}..., "
            f"estimated_cost=${estimated_cost:.6f}): {e}",
            exc_info=True
        )
        # Allow request to proceed to prevent blocking legitimate users
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
    
    # Use atomic Lua script to record cost
    try:
        await redis.eval(
            RECORD_COST_LUA,
            2,  # Number of keys
            cost_key,
            daily_cost_key_with_date,
            now,  # ARGV[1]
            unique_request_member,  # ARGV[2]
            high_cost_window_seconds + 60,  # ARGV[3] - window TTL
            172800,  # ARGV[4] - daily TTL (2 days)
        )
    except Exception as e:
        # Fail-open strategy: log error and continue silently
        logger.error(
            f"Error executing record cost Lua script for fingerprint {fingerprint[:20] if fingerprint else 'None'}... "
            f"(stable_identifier: {stable_identifier[:20] if stable_identifier else 'None'}..., "
            f"actual_cost=${actual_cost:.6f}): {e}",
            exc_info=True
        )
        # Continue silently - don't block the request flow

