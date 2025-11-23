"""
Challenge-Response Fingerprinting Module

This module provides challenge generation and validation for challenge-response fingerprinting.
Challenges are server-generated, one-time-use tokens that must be included in the client's fingerprint.
This prevents fingerprint replay attacks by making fingerprints unique per challenge.
"""

import os
import secrets
import time
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Environment variables
CHALLENGE_TTL_SECONDS = int(os.getenv("CHALLENGE_TTL_SECONDS", "300"))  # 5 minutes default
# In development mode, allow more active challenges to avoid 429 errors during rapid page loads
is_dev = os.getenv("ENVIRONMENT", "production").lower() == "development" or os.getenv("DEBUG", "false").lower() == "true"
if is_dev:
    MAX_ACTIVE_CHALLENGES_PER_IDENTIFIER = int(os.getenv("MAX_ACTIVE_CHALLENGES_PER_IDENTIFIER", "100"))
else:
    MAX_ACTIVE_CHALLENGES_PER_IDENTIFIER = int(os.getenv("MAX_ACTIVE_CHALLENGES_PER_IDENTIFIER", "3"))
ENABLE_CHALLENGE_RESPONSE = os.getenv("ENABLE_CHALLENGE_RESPONSE", "true").lower() == "true"


async def generate_challenge(identifier: str) -> Dict[str, Any]:
    """
    Generate a new challenge for the given identifier.
    
    Args:
        identifier: Client identifier (fingerprint or IP address)
    
    Returns:
        Dictionary with challenge_id and expires_in_seconds
    
    Raises:
        HTTPException: If identifier has too many active challenges
    """
    if not ENABLE_CHALLENGE_RESPONSE:
        # If disabled, return a dummy challenge (for backward compatibility)
        return {
            "challenge": "disabled",
            "expires_in_seconds": CHALLENGE_TTL_SECONDS
        }
    
    redis = await get_redis_client()
    now = int(time.time())
    
    # Track active challenges per identifier
    active_challenges_key = f"challenge:active:{identifier}"
    
    # Remove expired challenges from active set
    # Use sorted set with expiry timestamp as score
    await redis.zremrangebyscore(active_challenges_key, 0, now - CHALLENGE_TTL_SECONDS)
    
    # Check current active challenge count
    current_active_count = await redis.zcard(active_challenges_key)
    if current_active_count >= MAX_ACTIVE_CHALLENGES_PER_IDENTIFIER:
        logger.warning(
            f"Too many active challenges for identifier {identifier}: {current_active_count}"
        )
        raise HTTPException(
            status_code=429,
            detail={
                "error": "too_many_challenges",
                "message": "Too many active security challenges. Please wait a moment and try again."
            }
        )
    
    # Generate unique challenge ID (64 hex chars = 32 bytes)
    challenge_id = secrets.token_hex(32)
    expiry_time = now + CHALLENGE_TTL_SECONDS
    
    # Store challenge in Redis with its expiry
    # Key: challenge:{challenge_id} -> value: identifier
    challenge_key = f"challenge:{challenge_id}"
    await redis.setex(challenge_key, CHALLENGE_TTL_SECONDS, identifier)
    
    # Add to active challenges sorted set for this identifier
    # Score is expiry time, member is challenge_id
    await redis.zadd(active_challenges_key, {challenge_id: expiry_time})
    await redis.expire(active_challenges_key, CHALLENGE_TTL_SECONDS + 60)  # Cleanup after TTL
    
    logger.debug(f"Generated challenge {challenge_id} for identifier {identifier}")
    
    return {
        "challenge": challenge_id,
        "expires_in_seconds": CHALLENGE_TTL_SECONDS
    }


async def validate_and_consume_challenge(challenge_id: str, identifier: str) -> bool:
    """
    Validate and consume a challenge (one-time use).
    
    Args:
        challenge_id: The challenge ID to validate
        identifier: The identifier (fingerprint or IP) claiming this challenge
    
    Returns:
        True if challenge is valid and was consumed successfully, False otherwise
    
    Raises:
        HTTPException: If challenge is invalid, missing, or already consumed
    """
    if not ENABLE_CHALLENGE_RESPONSE:
        # If disabled, always allow (for backward compatibility)
        return True
    
    if not challenge_id or challenge_id == "disabled":
        # No challenge provided or disabled
        return True  # Allow for backward compatibility during rollout
    
    redis = await get_redis_client()
    
    # Check if challenge exists
    challenge_key = f"challenge:{challenge_id}"
    stored_identifier = await redis.get(challenge_key)
    
    if not stored_identifier:
        logger.warning(
            f"Challenge validation failed: challenge {challenge_id} not found or expired"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "invalid_challenge",
                "message": "Invalid or expired security challenge. Please request a new challenge."
            }
        )
    
    # Verify the challenge was issued to this identifier
    if stored_identifier != identifier:
        logger.warning(
            f"Challenge validation failed: challenge {challenge_id} issued to {stored_identifier} but used by {identifier}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "invalid_challenge",
                "message": "Security challenge mismatch. Please request a new challenge."
            }
        )
    
    # Consume the challenge (delete it for one-time use)
    await redis.delete(challenge_key)
    
    # Remove from active challenges set
    active_challenges_key = f"challenge:active:{identifier}"
    await redis.zrem(active_challenges_key, challenge_id)
    
    logger.debug(f"Challenge {challenge_id} validated and consumed for identifier {identifier}")
    
    return True


async def cleanup_expired_challenges():
    """
    Cleanup expired challenges from Redis (maintenance task).
    This can be called periodically to clean up stale challenge data.
    """
    if not ENABLE_CHALLENGE_RESPONSE:
        return
    
    redis = await get_redis_client()
    now = int(time.time())
    
    # Cleanup expired challenges from active sets
    # Note: This is best-effort cleanup. Challenges also expire via TTL.
    # This function can be called periodically for additional cleanup.
    try:
        # Find all active challenge keys
        pattern = "challenge:active:*"
        cursor = 0
        cleaned_count = 0
        
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                # Remove expired challenges
                removed = await redis.zremrangebyscore(key, 0, now - CHALLENGE_TTL_SECONDS)
                cleaned_count += removed
            
            if cursor == 0:
                break
        
        if cleaned_count > 0:
            logger.debug(f"Cleaned up {cleaned_count} expired challenges")
    except Exception as e:
        logger.error(f"Error during challenge cleanup: {e}", exc_info=True)

