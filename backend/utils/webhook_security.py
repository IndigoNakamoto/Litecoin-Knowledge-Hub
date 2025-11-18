"""
Webhook security utilities for Payload CMS webhook authentication and validation.
Implements HMAC signature verification, IP allowlisting, and replay attack prevention.
"""

import os
import hmac
import hashlib
import time
import logging
from typing import Optional, List, Dict, Any
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# Webhook security configuration
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_ALLOWED_IPS = os.getenv("WEBHOOK_ALLOWED_IPS", "").split(",") if os.getenv("WEBHOOK_ALLOWED_IPS") else []
WEBHOOK_ALLOWED_IPS = [ip.strip() for ip in WEBHOOK_ALLOWED_IPS if ip.strip()]

# Replay attack prevention: maximum age of webhook (in seconds)
WEBHOOK_MAX_AGE = int(os.getenv("WEBHOOK_MAX_AGE", "300"))  # 5 minutes default

# In-memory nonce store for replay prevention (simple implementation)
# In production, consider using Redis for distributed systems
_nonce_store: Dict[str, float] = {}
_nonce_store_cleanup_interval = 3600  # Clean up old nonces every hour
_last_cleanup = time.time()


def _cleanup_old_nonces():
    """Remove nonces older than WEBHOOK_MAX_AGE from memory."""
    global _last_cleanup
    current_time = time.time()
    
    if current_time - _last_cleanup > _nonce_store_cleanup_interval:
        expired_threshold = current_time - WEBHOOK_MAX_AGE
        expired_nonces = [nonce for nonce, timestamp in _nonce_store.items() if timestamp < expired_threshold]
        for nonce in expired_nonces:
            del _nonce_store[nonce]
        _last_cleanup = current_time
        if expired_nonces:
            logger.debug(f"Cleaned up {len(expired_nonces)} expired nonces")


def _get_client_ip(request: Request) -> str:
    """
    Extract client IP from request, respecting proxy headers.
    """
    # Check Cloudflare header first
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    
    # Check X-Forwarded-For header
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # X-Forwarded-For can contain multiple IPs, first is the original client
        return xff.split(",")[0].strip()
    
    # Fallback to direct client host
    if request.client:
        return request.client.host
    
    return "unknown"


def _verify_ip_allowed(client_ip: str) -> bool:
    """
    Verify if client IP is in the allowed list.
    If no allowed IPs are configured, IP checking is disabled.
    """
    if not WEBHOOK_ALLOWED_IPS:
        # No IP allowlist configured - IP checking disabled
        logger.debug("No webhook IP allowlist configured, IP check disabled")
        return True
    
    if client_ip in WEBHOOK_ALLOWED_IPS:
        return True
    
    logger.warning(f"Webhook request from unauthorized IP: {client_ip} (allowed: {WEBHOOK_ALLOWED_IPS})")
    return False


def _verify_hmac_signature(payload_body: bytes, signature_header: Optional[str], secret: str) -> bool:
    """
    Verify HMAC SHA-256 signature of webhook payload.
    
    Args:
        payload_body: Raw request body bytes
        signature_header: Signature from X-Payload-Signature header
        secret: Shared secret for HMAC verification
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        logger.warning("Missing webhook signature header")
        return False
    
    if not secret:
        logger.error("WEBHOOK_SECRET not configured")
        return False
    
    try:
        # Compute expected signature
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures using constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature_header)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}", exc_info=True)
        return False


def _verify_timestamp(timestamp: Optional[float]) -> bool:
    """
    Verify webhook timestamp to prevent replay attacks.
    
    Args:
        timestamp: Unix timestamp from webhook payload
    
    Returns:
        True if timestamp is valid and within acceptable age, False otherwise
    """
    if not timestamp:
        # If no timestamp provided, skip timestamp verification
        # (but this should be logged as a warning)
        logger.warning("Webhook payload missing timestamp")
        return True  # Allow for backward compatibility
    
    current_time = time.time()
    age = current_time - timestamp
    
    if age < 0:
        # Future timestamp indicates clock skew or tampering
        logger.warning(f"Webhook timestamp is in the future: {timestamp} (current: {current_time})")
        return False
    
    if age > WEBHOOK_MAX_AGE:
        # Timestamp too old
        logger.warning(f"Webhook timestamp too old: {age:.0f}s (max: {WEBHOOK_MAX_AGE}s)")
        return False
    
    return True


def _verify_nonce(nonce: Optional[str]) -> bool:
    """
    Verify webhook nonce to prevent replay attacks.
    
    Args:
        nonce: Unique nonce from webhook payload
    
    Returns:
        True if nonce is valid and not seen before, False otherwise
    """
    if not nonce:
        # If no nonce provided, skip nonce verification
        # (timestamp verification will still prevent old replays)
        return True
    
    # Clean up old nonces periodically
    _cleanup_old_nonces()
    
    current_time = time.time()
    
    # Check if nonce was already used
    if nonce in _nonce_store:
        logger.warning(f"Webhook nonce reuse detected: {nonce}")
        return False
    
    # Store nonce with current timestamp
    _nonce_store[nonce] = current_time
    
    return True


async def verify_webhook_request(request: Request, payload_body: bytes) -> None:
    """
    Verify webhook request authenticity and prevent replay attacks.
    
    This function implements multiple security layers:
    1. IP allowlisting (optional, if WEBHOOK_ALLOWED_IPS is configured)
    2. HMAC signature verification (if WEBHOOK_SECRET is configured)
    3. Timestamp validation to prevent old replay attacks
    4. Nonce validation to prevent duplicate requests
    
    Args:
        request: FastAPI Request object
        payload_body: Raw request body bytes
    
    Raises:
        HTTPException: If webhook verification fails
    """
    # If webhook security is disabled (no secret configured), allow all requests
    # This is for backward compatibility and development
    if not WEBHOOK_SECRET:
        logger.warning("Webhook security disabled: WEBHOOK_SECRET not configured")
        return
    
    # 1. IP allowlisting (optional)
    client_ip = _get_client_ip(request)
    if not _verify_ip_allowed(client_ip):
        logger.warning(f"Webhook request rejected: unauthorized IP {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "unauthorized_ip", "message": "Webhook request from unauthorized IP address"}
        )
    
    # 2. HMAC signature verification
    signature_header = request.headers.get("X-Payload-Signature") or request.headers.get("X-Webhook-Signature")
    if not _verify_hmac_signature(payload_body, signature_header, WEBHOOK_SECRET):
        logger.warning("Webhook request rejected: invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_signature", "message": "Webhook signature verification failed"}
        )
    
    # 3. Parse payload to extract timestamp and nonce (if present)
    try:
        import json
        payload = json.loads(payload_body.decode('utf-8'))
        timestamp = payload.get('timestamp') or payload.get('time')
        nonce = payload.get('nonce') or payload.get('id')  # Use id as fallback nonce
        
        # Convert timestamp to float if it's provided
        if timestamp:
            if isinstance(timestamp, str):
                try:
                    timestamp = float(timestamp)
                except ValueError:
                    logger.warning(f"Invalid timestamp format: {timestamp}")
                    timestamp = None
            elif isinstance(timestamp, (int, float)):
                timestamp = float(timestamp)
        
        # 4. Timestamp validation
        if not _verify_timestamp(timestamp):
            logger.warning(f"Webhook request rejected: invalid timestamp {timestamp}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_timestamp", "message": "Webhook timestamp validation failed"}
            )
        
        # 5. Nonce validation
        if not _verify_nonce(nonce):
            logger.warning(f"Webhook request rejected: nonce reuse detected")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "nonce_reused", "message": "Webhook nonce has already been used"}
            )
        
    except json.JSONDecodeError as e:
        logger.warning(f"Webhook request rejected: invalid JSON payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_payload", "message": "Webhook payload is not valid JSON"}
        )
    except Exception as e:
        # Log error but don't expose details to client
        logger.error(f"Error during webhook verification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "verification_error", "message": "Webhook verification failed"}
        )
    
    logger.debug(f"Webhook request verified successfully from IP: {client_ip}")

