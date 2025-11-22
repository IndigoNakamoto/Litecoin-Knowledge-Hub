"""
Cloudflare Turnstile verification utility.

This module provides integration with Cloudflare Turnstile for bot protection.
Turnstile is a privacy-focused CAPTCHA alternative that verifies user interactions
without showing traditional CAPTCHA puzzles.
"""

import os
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)

# Environment variables
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")
ENABLE_TURNSTILE = os.getenv("ENABLE_TURNSTILE", "false").lower() == "true"

# Cloudflare Turnstile API endpoint
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def is_turnstile_enabled() -> bool:
    """
    Check if Turnstile verification is enabled.
    
    Returns:
        True if Turnstile is enabled and configured, False otherwise
    """
    return ENABLE_TURNSTILE and bool(TURNSTILE_SECRET_KEY)


async def verify_turnstile_token(
    token: str,
    remoteip: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify a Cloudflare Turnstile token.
    
    Args:
        token: Turnstile token from client
        remoteip: Optional client IP address for additional verification
    
    Returns:
        Dictionary with verification result:
        - success: bool - Whether verification succeeded
        - error-codes: list - List of error codes if verification failed
        - challenge_ts: str - Timestamp when challenge was completed (if successful)
        - hostname: str - Hostname where challenge was completed (if successful)
        - action: str - Action identifier (if provided in widget)
        - cdata: str - Customer data (if provided in widget)
    """
    if not is_turnstile_enabled():
        # Turnstile disabled, return skip result
        logger.debug("Turnstile verification disabled, skipping verification")
        return {
            "success": True,
            "skip": True,
            "message": "Turnstile verification is disabled"
        }
    
    if not token:
        # No token provided
        logger.warning("Turnstile verification failed: no token provided")
        return {
            "success": False,
            "error-codes": ["missing-input-response"]
        }
    
    try:
        # Prepare request data
        data = {
            "secret": TURNSTILE_SECRET_KEY,
            "response": token,
        }
        
        if remoteip:
            data["remoteip"] = remoteip
        
        # Send verification request to Cloudflare
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(TURNSTILE_VERIFY_URL, data=data)
            response.raise_for_status()
            result = response.json()
        
        # Log result (without exposing sensitive data)
        if result.get("success"):
            logger.debug(f"Turnstile verification successful for IP: {remoteip or 'unknown'}")
        else:
            error_codes = result.get("error-codes", [])
            logger.warning(
                f"Turnstile verification failed for IP: {remoteip or 'unknown'}, "
                f"errors: {error_codes}"
            )
        
        return result
        
    except httpx.TimeoutException:
        logger.error("Turnstile API request timed out")
        # Return error result (will trigger graceful degradation)
        return {
            "success": False,
            "error-codes": ["timeout"]
        }
    except httpx.RequestError as e:
        logger.error(f"Turnstile API request failed: {e}")
        # Return error result (will trigger graceful degradation)
        return {
            "success": False,
            "error-codes": ["network-error"]
        }
    except Exception as e:
        logger.error(f"Unexpected error during Turnstile verification: {e}", exc_info=True)
        # Return error result (will trigger graceful degradation)
        return {
            "success": False,
            "error-codes": ["internal-error"]
        }

