"""
Admin API endpoints for authentication.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import logging
import os
import hmac

from backend.rate_limiter import RateLimitConfig, check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting configuration for admin auth endpoints
ADMIN_AUTH_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=10,
    requests_per_hour=100,
    identifier="admin_auth",
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


@router.post("/login")
async def admin_login(request: Request) -> Dict[str, Any]:
    """
    Verify admin token and return session info.
    
    Requires Bearer token authentication via Authorization header.
    Example: Authorization: Bearer <ADMIN_TOKEN>
    
    Returns:
        Dictionary with authentication status and session info.
    """
    # Rate limiting
    await check_rate_limit(request, ADMIN_AUTH_RATE_LIMIT)
    
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    
    # Verify authentication
    if not verify_admin_token(auth_header):
        logger.warning(
            f"Unauthorized admin login attempt from IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "Invalid or missing admin token"}
        )
    
    return {
        "authenticated": True,
        "message": "Authentication successful"
    }


@router.get("/verify")
async def verify_admin(request: Request) -> Dict[str, Any]:
    """
    Verify current admin session/token.
    
    Requires Bearer token authentication via Authorization header.
    Example: Authorization: Bearer <ADMIN_TOKEN>
    
    Returns:
        Dictionary with authentication status.
    """
    # Rate limiting
    await check_rate_limit(request, ADMIN_AUTH_RATE_LIMIT)
    
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    
    # Verify authentication
    if not verify_admin_token(auth_header):
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "Invalid or missing admin token"}
        )
    
    return {
        "authenticated": True,
        "message": "Token is valid"
    }

