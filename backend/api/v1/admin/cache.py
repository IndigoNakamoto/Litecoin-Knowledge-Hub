"""
Admin API endpoints for cache management.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import logging
import os
import hmac

from backend.cache_utils import suggested_question_cache
from backend.rate_limiter import RateLimitConfig, check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting configuration for admin cache endpoints
ADMIN_CACHE_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=10,
    requests_per_hour=100,
    identifier="admin_cache",
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


@router.get("/suggested-questions/stats")
async def get_cache_stats(request: Request) -> Dict[str, Any]:
    """
    Get statistics about the suggested questions cache.
    
    Requires Bearer token authentication via Authorization header.
    
    Returns:
        Dictionary with cache statistics.
    """
    # Rate limiting
    await check_rate_limit(request, ADMIN_CACHE_RATE_LIMIT)
    
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    
    # Verify authentication
    if not verify_admin_token(auth_header):
        logger.warning(
            f"Unauthorized cache stats access attempt from IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "Invalid or missing admin token"}
        )
    
    try:
        cache_size = await suggested_question_cache.get_cache_size()
        
        return {
            "cache_size": cache_size,
            "cache_type": "suggested_questions"
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": "Failed to retrieve cache stats"}
        )


@router.post("/suggested-questions/clear")
async def clear_suggested_questions_cache(request: Request) -> Dict[str, Any]:
    """
    Clear the suggested questions cache.
    
    This deletes all keys matching the pattern: suggested_question:*
    
    Requires Bearer token authentication via Authorization header.
    
    Returns:
        Dictionary with operation result.
    """
    # Rate limiting
    await check_rate_limit(request, ADMIN_CACHE_RATE_LIMIT)
    
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    
    # Verify authentication
    if not verify_admin_token(auth_header):
        logger.warning(
            f"Unauthorized cache clear attempt from IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "Invalid or missing admin token"}
        )
    
    try:
        # Get cache size before clearing
        cache_size_before = await suggested_question_cache.get_cache_size()
        
        # Clear the cache
        await suggested_question_cache.clear()
        
        logger.info(f"Admin cleared suggested questions cache ({cache_size_before} entries)")
        
        return {
            "success": True,
            "cleared_count": cache_size_before,
            "message": f"Cleared {cache_size_before} entries from suggested questions cache"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": "Failed to clear cache"}
        )


@router.post("/suggested-questions/refresh")
async def refresh_suggested_questions_cache(request: Request) -> Dict[str, Any]:
    """
    Regenerate the suggested questions cache.
    
    This triggers a background refresh of the cache by pre-generating responses
    for all active suggested questions.
    
    Requires Bearer token authentication via Authorization header.
    
    Returns:
        Dictionary with operation result.
    """
    # Rate limiting
    await check_rate_limit(request, ADMIN_CACHE_RATE_LIMIT)
    
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    
    # Verify authentication
    if not verify_admin_token(auth_header):
        logger.warning(
            f"Unauthorized cache refresh attempt from IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "Invalid or missing admin token"}
        )
    
    try:
        # Import the refresh function from main.py
        from backend.main import refresh_suggested_question_cache
        
        # Trigger the refresh (this runs in the background)
        result = await refresh_suggested_question_cache()
        
        logger.info("Admin triggered suggested questions cache refresh")
        
        return {
            "success": True,
            "message": "Cache refresh initiated. This may take a few minutes to complete.",
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": "Failed to refresh cache"}
        )

