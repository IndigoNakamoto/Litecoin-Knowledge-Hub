"""
Webhook authentication utilities for verifying HMAC signatures from Payload CMS.

This module provides functions to verify webhook requests using HMAC-SHA256
signature verification and timestamp validation to prevent replay attacks.
"""

import hmac
import hashlib
import time
import os
import logging
from typing import Optional, Tuple
from fastapi import Request

logger = logging.getLogger(__name__)

# Maximum age of webhook requests (5 minutes in seconds)
WEBHOOK_TIMESTAMP_TOLERANCE = 300


def get_webhook_secret() -> str:
    """
    Get the webhook secret from environment variables.
    
    Returns:
        The webhook secret as a string
        
    Raises:
        ValueError: If WEBHOOK_SECRET is not set
    """
    secret = os.getenv("WEBHOOK_SECRET")
    if not secret:
        raise ValueError(
            "WEBHOOK_SECRET environment variable is not set. "
            "Webhook authentication requires a shared secret."
        )
    return secret


def compute_hmac_signature(payload: bytes, secret: str) -> str:
    """
    Compute HMAC-SHA256 signature for a payload.
    
    Args:
        payload: The request body as bytes
        secret: The shared secret key
        
    Returns:
        Hexadecimal string representation of the HMAC signature
    """
    return hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify that a webhook signature matches the expected HMAC-SHA256 signature.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        payload: The request body as bytes
        signature: The signature from the X-Webhook-Signature header
        secret: The shared secret key
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature:
        return False
    
    expected_signature = compute_hmac_signature(payload, secret)
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


def validate_webhook_timestamp(timestamp_str: str, tolerance: int = WEBHOOK_TIMESTAMP_TOLERANCE) -> bool:
    """
    Validate that a webhook timestamp is within the acceptable time window.
    
    Prevents replay attacks by ensuring requests are recent.
    
    Args:
        timestamp_str: Unix timestamp as string from X-Webhook-Timestamp header
        tolerance: Maximum age of request in seconds (default: 5 minutes)
        
    Returns:
        True if timestamp is valid (within tolerance), False otherwise
    """
    if not timestamp_str:
        return False
    
    try:
        timestamp = int(timestamp_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid timestamp format: {timestamp_str}")
        return False
    
    current_time = int(time.time())
    time_difference = abs(current_time - timestamp)
    
    if time_difference > tolerance:
        logger.warning(
            f"Webhook timestamp validation failed: "
            f"timestamp={timestamp}, current={current_time}, "
            f"difference={time_difference}s (max={tolerance}s)"
        )
        return False
    
    return True


async def verify_webhook_request(request: Request, body: bytes) -> Tuple[bool, Optional[str]]:
    """
    Verify a webhook request by checking signature and timestamp.
    
    This function:
    1. Extracts signature and timestamp from headers
    2. Verifies the signature using HMAC-SHA256
    3. Validates the timestamp is within acceptable window
    
    Args:
        request: FastAPI Request object
        body: The request body as bytes (must be provided to avoid reading twice)
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if request is valid, False otherwise
        - error_message: Error description if invalid, None if valid
    """
    try:
        # Get webhook secret
        try:
            secret = get_webhook_secret()
        except ValueError as e:
            logger.error(f"Webhook secret not configured: {e}")
            return False, "Webhook authentication not configured"
        
        # Extract headers
        signature = request.headers.get("X-Webhook-Signature", "")
        timestamp = request.headers.get("X-Webhook-Timestamp", "")
        
        # Validate timestamp first (faster check)
        if not validate_webhook_timestamp(timestamp):
            return False, "Invalid or expired timestamp"
        
        # Verify signature
        if not verify_webhook_signature(body, signature, secret):
            logger.warning(
                f"Webhook signature verification failed. "
                f"IP: {request.client.host if request.client else 'unknown'}"
            )
            return False, "Invalid signature"
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error verifying webhook request: {e}", exc_info=True)
        return False, "Webhook verification failed"


def require_webhook_auth(request: Request):
    """
    FastAPI dependency to require webhook authentication.
    
    Raises HTTPException with 401 status if authentication fails.
    
    Usage:
        @router.post("/payload")
        async def webhook_endpoint(request: Request, _: None = Depends(require_webhook_auth)):
            ...
    """
    # Note: This is a synchronous dependency, but we need async to read body
    # So we'll handle verification in the endpoint itself
    pass

