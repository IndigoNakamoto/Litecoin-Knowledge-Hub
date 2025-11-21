"""
Admin API endpoint for LLM usage statistics.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import logging
import os
import hmac

from backend.monitoring.spend_limit import get_current_usage
from backend.rate_limiter import RateLimitConfig, check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting configuration for admin usage endpoints
ADMIN_USAGE_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=30,
    requests_per_hour=200,
    identifier="admin_usage",
    enable_progressive_limits=True,
)


def verify_admin_token(authorization: str = None) -> bool:
    """
    Verify admin token from Authorization header.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
        
    Returns:
        True if token is valid, False otherwise
    """
    if not authorization:
        return False
    
    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return False
    except ValueError:
        return False
    
    # Get expected token from environment
    expected_token = os.getenv("ADMIN_TOKEN")
    if not expected_token:
        logger.warning("ADMIN_TOKEN not set, admin endpoint authentication disabled")
        return False
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(token, expected_token)


@router.get("/usage")
async def get_usage(request: Request) -> Dict[str, Any]:
    """
    Get current daily and hourly LLM usage statistics.
    
    Requires Bearer token authentication via Authorization header.
    Example: Authorization: Bearer <ADMIN_TOKEN>
    
    Returns:
        Dictionary with daily and hourly usage information including costs, limits, percentages, and tokens.
    """
    # Rate limiting
    await check_rate_limit(request, ADMIN_USAGE_RATE_LIMIT)
    
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    
    # Verify authentication
    if not verify_admin_token(auth_header):
        logger.warning(
            f"Unauthorized usage statistics access attempt from IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "Invalid or missing admin token"}
        )
    
    try:
        usage_info = await get_current_usage()
        return usage_info
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": "Failed to retrieve usage statistics"}
        )


@router.get("/usage/status")
async def get_usage_status(request: Request) -> Dict[str, Any]:
    """
    Get simplified usage status for frontend warnings.
    Returns warning level if approaching limits.
    
    This endpoint is PUBLIC (no authentication required) to allow the frontend
    to display usage warnings to users. It only returns percentages and warning
    levels, not sensitive cost information.
    
    Returns:
        Dictionary with status, warning level, and usage percentages (no cost data).
    """
    # Rate limiting (more lenient for public endpoint)
    await check_rate_limit(request, ADMIN_USAGE_RATE_LIMIT)
    
    try:
        usage_info = await get_current_usage()
        
        daily_percentage = usage_info["daily"]["percentage_used"]
        hourly_percentage = usage_info["hourly"]["percentage_used"]
        
        # Determine warning level
        warning_level = None
        if daily_percentage >= 100 or hourly_percentage >= 100:
            warning_level = "error"
        elif daily_percentage >= 80 or hourly_percentage >= 80:
            warning_level = "warning"
        elif daily_percentage >= 60 or hourly_percentage >= 60:
            warning_level = "info"
        
        # Return only percentages and warning level (no cost information)
        return {
            "status": "ok" if warning_level is None else warning_level,
            "warning_level": warning_level,
            "daily_percentage": daily_percentage,
            "hourly_percentage": hourly_percentage,
            # Note: Removed daily_remaining and hourly_remaining to avoid cost information disclosure
        }
    except Exception as e:
        logger.error(f"Error getting usage status: {e}", exc_info=True)
        # Return safe defaults on error
        return {
            "status": "ok",
            "warning_level": None,
            "daily_percentage": 0.0,
            "hourly_percentage": 0.0,
        }

