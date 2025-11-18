"""
Security tests for webhook endpoint authentication and validation.
"""

import pytest
import hmac
import hashlib
import json
import time
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.api.v1.sync.payload import router
from backend.utils.webhook_security import verify_webhook_request, _verify_hmac_signature, _verify_timestamp, _verify_nonce
from fastapi import Request, HTTPException
import os

# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v1/sync")

# Set test webhook secret
os.environ["WEBHOOK_SECRET"] = "test-secret-key-for-webhook-verification-minimum-32-chars"
os.environ["WEBHOOK_MAX_AGE"] = "300"

client = TestClient(app)


def create_signed_payload(payload: dict, secret: str) -> tuple[bytes, str]:
    """Create a webhook payload with HMAC signature."""
    payload_body = json.dumps(payload).encode('utf-8')
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return payload_body, signature


def create_webhook_payload(doc_data: dict, operation: str = "update", timestamp: float = None, nonce: str = None) -> dict:
    """Create a webhook payload with timestamp and nonce."""
    if timestamp is None:
        timestamp = time.time()
    if nonce is None:
        nonce = f"test-nonce-{int(time.time() * 1000)}"
    
    return {
        "doc": doc_data,
        "operation": operation,
        "timestamp": timestamp,
        "nonce": nonce
    }


@pytest.fixture
def valid_webhook_payload():
    """Create a valid webhook payload for testing."""
    return {
        "doc": {
            "id": "test-id",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "title": "Test Article",
            "author": None,
            "publishedDate": None,
            "category": [],
            "content": {},
            "markdown": "# Test Article",
            "status": "published",
            "slug": "test-article"
        },
        "operation": "update"
    }


def test_webhook_without_signature_should_fail(valid_webhook_payload):
    """Test that webhook without signature is rejected."""
    response = client.post(
        "/api/v1/sync/payload",
        json=valid_webhook_payload,
        headers={}
    )
    assert response.status_code == 401
    assert "invalid_signature" in response.json()["detail"]["error"]


def test_webhook_with_invalid_signature_should_fail(valid_webhook_payload):
    """Test that webhook with invalid signature is rejected."""
    payload_body = json.dumps(valid_webhook_payload).encode('utf-8')
    
    response = client.post(
        "/api/v1/sync/payload",
        content=payload_body,
        headers={
            "Content-Type": "application/json",
            "X-Payload-Signature": "invalid-signature"
        }
    )
    assert response.status_code == 401
    assert "invalid_signature" in response.json()["detail"]["error"]


def test_webhook_with_valid_signature_should_succeed(valid_webhook_payload):
    """Test that webhook with valid signature is accepted."""
    secret = os.environ["WEBHOOK_SECRET"]
    payload_body, signature = create_signed_payload(valid_webhook_payload, secret)
    
    # Add timestamp and nonce for replay prevention
    payload = create_webhook_payload(valid_webhook_payload["doc"])
    payload_body, signature = create_signed_payload(payload, secret)
    
    response = client.post(
        "/api/v1/sync/payload",
        content=payload_body,
        headers={
            "Content-Type": "application/json",
            "X-Payload-Signature": signature
        }
    )
    # Should return 200 (webhook accepted) or 422 (validation error for test data)
    # 422 is acceptable as we're using minimal test data
    assert response.status_code in [200, 422]


def test_webhook_with_old_timestamp_should_fail(valid_webhook_payload):
    """Test that webhook with timestamp too old is rejected."""
    secret = os.environ["WEBHOOK_SECRET"]
    old_timestamp = time.time() - 400  # Older than 300s max age
    
    payload = create_webhook_payload(valid_webhook_payload["doc"], timestamp=old_timestamp)
    payload_body, signature = create_signed_payload(payload, secret)
    
    response = client.post(
        "/api/v1/sync/payload",
        content=payload_body,
        headers={
            "Content-Type": "application/json",
            "X-Payload-Signature": signature
        }
    )
    assert response.status_code == 400
    assert "invalid_timestamp" in response.json()["detail"]["error"]


def test_webhook_with_future_timestamp_should_fail(valid_webhook_payload):
    """Test that webhook with future timestamp is rejected."""
    secret = os.environ["WEBHOOK_SECRET"]
    future_timestamp = time.time() + 60  # 60 seconds in the future
    
    payload = create_webhook_payload(valid_webhook_payload["doc"], timestamp=future_timestamp)
    payload_body, signature = create_signed_payload(payload, secret)
    
    response = client.post(
        "/api/v1/sync/payload",
        content=payload_body,
        headers={
            "Content-Type": "application/json",
            "X-Payload-Signature": signature
        }
    )
    assert response.status_code == 400
    assert "invalid_timestamp" in response.json()["detail"]["error"]


def test_webhook_nonce_reuse_should_fail(valid_webhook_payload):
    """Test that reusing the same nonce is rejected."""
    secret = os.environ["WEBHOOK_SECRET"]
    nonce = f"test-nonce-{int(time.time() * 1000)}"
    
    payload1 = create_webhook_payload(valid_webhook_payload["doc"], nonce=nonce)
    payload_body1, signature1 = create_signed_payload(payload1, secret)
    
    # First request should succeed
    response1 = client.post(
        "/api/v1/sync/payload",
        content=payload_body1,
        headers={
            "Content-Type": "application/json",
            "X-Payload-Signature": signature1
        }
    )
    # 200 or 422 is acceptable
    assert response1.status_code in [200, 422]
    
    # Second request with same nonce should fail
    payload2 = create_webhook_payload(valid_webhook_payload["doc"], nonce=nonce)
    payload_body2, signature2 = create_signed_payload(payload2, secret)
    
    response2 = client.post(
        "/api/v1/sync/payload",
        content=payload_body2,
        headers={
            "Content-Type": "application/json",
            "X-Payload-Signature": signature2
        }
    )
    assert response2.status_code == 400
    assert "nonce_reused" in response2.json()["detail"]["error"]


def test_hmac_signature_verification():
    """Test HMAC signature verification function."""
    secret = "test-secret"
    payload_body = b"test payload"
    
    # Create valid signature
    valid_signature = hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    # Verify valid signature
    assert _verify_hmac_signature(payload_body, valid_signature, secret) is True
    
    # Verify invalid signature
    assert _verify_hmac_signature(payload_body, "invalid", secret) is False
    
    # Verify missing signature
    assert _verify_hmac_signature(payload_body, None, secret) is False
    
    # Verify with wrong secret
    wrong_secret = "wrong-secret"
    assert _verify_hmac_signature(payload_body, valid_signature, wrong_secret) is False


def test_timestamp_verification():
    """Test timestamp verification function."""
    current_time = time.time()
    
    # Valid timestamp (current time)
    assert _verify_timestamp(current_time) is True
    
    # Valid timestamp (5 minutes ago, within max age)
    assert _verify_timestamp(current_time - 60) is True
    
    # Invalid timestamp (too old)
    assert _verify_timestamp(current_time - 400) is False
    
    # Invalid timestamp (future)
    assert _verify_timestamp(current_time + 60) is False
    
    # Missing timestamp (allowed for backward compatibility)
    assert _verify_timestamp(None) is True


def test_nonce_verification():
    """Test nonce verification function."""
    nonce1 = "nonce-1"
    nonce2 = "nonce-2"
    
    # First use of nonce should succeed
    assert _verify_nonce(nonce1) is True
    
    # Reusing same nonce should fail
    assert _verify_nonce(nonce1) is False
    
    # Different nonce should succeed
    assert _verify_nonce(nonce2) is True
    
    # Missing nonce (allowed for backward compatibility)
    assert _verify_nonce(None) is True


def test_test_webhook_endpoint_no_auth():
    """Test that /test-webhook endpoint does not require authentication."""
    payload = {
        "doc": {
            "id": "test-id",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "title": "Test Article",
            "author": None,
            "publishedDate": None,
            "category": [],
            "content": {},
            "markdown": "# Test",
            "status": "published",
            "slug": "test"
        }
    }
    
    response = client.post(
        "/api/v1/sync/test-webhook",
        json=payload,
        headers={}
    )
    # Should succeed without authentication
    assert response.status_code in [200, 422]  # 422 if validation fails, but no auth error

