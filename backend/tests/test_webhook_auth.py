#!/usr/bin/env python3
"""
Test script for webhook authentication (HMAC signature verification).

This script tests the webhook authentication implementation by:
1. Testing authenticated requests (with valid signatures)
2. Testing unauthenticated requests (should fail)
3. Testing invalid signatures (should fail)
4. Testing expired timestamps (should fail)
5. Testing missing headers (should fail)
"""

import requests
import json
import sys
import os
import hmac
import hashlib
import time
from datetime import datetime

def generate_hmac_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for a payload."""
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def test_authenticated_webhook(backend_url="http://localhost:8000", webhook_secret=None):
    """Test webhook with valid authentication."""
    print("\n✅ Test 1: Authenticated webhook (should succeed)")
    print("-" * 60)
    
    if not webhook_secret:
        print("⚠️  WEBHOOK_SECRET not provided, skipping authenticated test")
        return False
    
    sample_payload = {
        "operation": "create",
        "doc": {
            "id": "test-auth-123",
            "title": "Test Authenticated Article",
            "content": {
                "root": {
                    "type": "root",
                    "children": [
                        {
                            "type": "paragraph",
                            "children": [
                                {
                                    "type": "text",
                                    "text": "This is a test article for authentication."
                                }
                            ]
                        }
                    ]
                }
            },
            "markdown": "This is a test article for authentication.",
            "status": "published",
            "author": "test-user",
            "publishedDate": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }
    }
    
    payload_str = json.dumps(sample_payload)
    timestamp = str(int(time.time()))
    signature = generate_hmac_signature(payload_str, webhook_secret)
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Timestamp": timestamp
    }
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/sync/payload",
            data=payload_str.encode('utf-8') if isinstance(payload_str, str) else payload_str,
            headers=headers,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Authenticated request succeeded!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Authenticated request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_unauthenticated_webhook(backend_url="http://localhost:8000"):
    """Test webhook without authentication (should fail)."""
    print("\n❌ Test 2: Unauthenticated webhook (should fail)")
    print("-" * 60)
    
    sample_payload = {
        "operation": "create",
        "doc": {
            "id": "test-unauth-123",
            "title": "Test Unauthenticated Article",
            "content": {
                "root": {
                    "type": "root",
                    "children": [
                        {
                            "type": "paragraph",
                            "children": [
                                {
                                    "type": "text",
                                    "text": "Test content"
                                }
                            ]
                        }
                    ]
                }
            },
            "markdown": "Test content",
            "status": "published",
            "author": "test-user",
            "publishedDate": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }
    }
    
    headers = {
        "Content-Type": "application/json"
        # No signature or timestamp headers
    }
    
    try:
        payload_str = json.dumps(sample_payload)
        response = requests.post(
            f"{backend_url}/api/v1/sync/payload",
            data=payload_str.encode('utf-8'),
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("✅ Unauthenticated request correctly rejected!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Expected 401, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_invalid_signature(backend_url="http://localhost:8000"):
    """Test webhook with invalid signature (should fail)."""
    print("\n❌ Test 3: Invalid signature (should fail)")
    print("-" * 60)
    
    sample_payload = {
        "operation": "create",
        "doc": {
            "id": "test-invalid-sig-123",
            "title": "Test Invalid Signature",
            "content": {
                "root": {
                    "type": "root",
                    "children": [
                        {
                            "type": "paragraph",
                            "children": [
                                {
                                    "type": "text",
                                    "text": "Test content"
                                }
                            ]
                        }
                    ]
                }
            },
            "markdown": "Test content",
            "status": "published",
            "author": "test-user",
            "publishedDate": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }
    }
    
    payload_str = json.dumps(sample_payload)
    timestamp = str(int(time.time()))
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": "invalid_signature_here",
        "X-Webhook-Timestamp": timestamp
    }
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/sync/payload",
            data=payload_str,
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("✅ Invalid signature correctly rejected!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Expected 401, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_expired_timestamp(backend_url="http://localhost:8000", webhook_secret=None):
    """Test webhook with expired timestamp (should fail)."""
    print("\n❌ Test 4: Expired timestamp (should fail)")
    print("-" * 60)
    
    if not webhook_secret:
        print("⚠️  WEBHOOK_SECRET not provided, skipping expired timestamp test")
        return False
    
    sample_payload = {
        "operation": "create",
        "doc": {
            "id": "test-expired-123",
            "title": "Test Expired Timestamp",
            "content": {
                "root": {
                    "type": "root",
                    "children": [
                        {
                            "type": "paragraph",
                            "children": [
                                {
                                    "type": "text",
                                    "text": "Test content"
                                }
                            ]
                        }
                    ]
                }
            },
            "markdown": "Test content",
            "status": "published",
            "author": "test-user",
            "publishedDate": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }
    }
    
    payload_str = json.dumps(sample_payload)
    # Use timestamp from 10 minutes ago (outside 5-minute window)
    expired_timestamp = str(int(time.time()) - 600)
    signature = generate_hmac_signature(payload_str, webhook_secret)
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Timestamp": expired_timestamp
    }
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/sync/payload",
            data=payload_str,
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("✅ Expired timestamp correctly rejected!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Expected 401, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_missing_timestamp(backend_url="http://localhost:8000", webhook_secret=None):
    """Test webhook with missing timestamp (should fail)."""
    print("\n❌ Test 5: Missing timestamp (should fail)")
    print("-" * 60)
    
    if not webhook_secret:
        print("⚠️  WEBHOOK_SECRET not provided, skipping missing timestamp test")
        return False
    
    sample_payload = {
        "operation": "create",
        "doc": {
            "id": "test-missing-ts-123",
            "title": "Test Missing Timestamp",
            "content": {
                "root": {
                    "type": "root",
                    "children": [
                        {
                            "type": "paragraph",
                            "children": [
                                {
                                    "type": "text",
                                    "text": "Test content"
                                }
                            ]
                        }
                    ]
                }
            },
            "markdown": "Test content",
            "status": "published",
            "author": "test-user",
            "publishedDate": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }
    }
    
    payload_str = json.dumps(sample_payload)
    signature = generate_hmac_signature(payload_str, webhook_secret)
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature
        # Missing X-Webhook-Timestamp
    }
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/sync/payload",
            data=payload_str,
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("✅ Missing timestamp correctly rejected!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Expected 401, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_test_endpoint_production(backend_url="http://localhost:8000"):
    """Test that test endpoint is disabled in production."""
    print("\n🔒 Test 6: Test endpoint in production (should be disabled)")
    print("-" * 60)
    
    sample_payload = {
        "operation": "create",
        "doc": {
            "id": "test-prod-123",
            "title": "Test Production Endpoint",
            "content": {
                "root": {
                    "type": "root",
                    "children": [
                        {
                            "type": "paragraph",
                            "children": [
                                {
                                    "type": "text",
                                    "text": "Test content"
                                }
                            ]
                        }
                    ]
                }
            },
            "markdown": "Test content",
            "status": "published",
            "author": "test-user",
            "publishedDate": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }
    }
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/sync/test-webhook",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        # In production, should return 404. In development, might return 200 or 401
        node_env = os.getenv("NODE_ENV", "").lower()
        if node_env == "production":
            if response.status_code == 404:
                print("✅ Test endpoint correctly disabled in production!")
                return True
            else:
                print(f"⚠️  Test endpoint accessible in production (status: {response.status_code})")
                return False
        else:
            print(f"ℹ️  Running in development mode (NODE_ENV={node_env})")
            print(f"Response: {response.json() if response.status_code < 500 else response.text}")
            return True  # Not a failure in dev mode
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function to run all webhook authentication tests."""
    backend_url = "http://localhost:8000"
    webhook_secret = os.getenv("WEBHOOK_SECRET")
    
    if len(sys.argv) > 1:
        backend_url = sys.argv[1]
    
    if len(sys.argv) > 2:
        webhook_secret = sys.argv[2]
    
    print("🔐 Webhook Authentication Test Suite")
    print("=" * 60)
    print(f"Backend URL: {backend_url}")
    print(f"WEBHOOK_SECRET: {'***' if webhook_secret else 'NOT SET'}")
    print("=" * 60)
    
    if not webhook_secret:
        print("\n⚠️  WARNING: WEBHOOK_SECRET not set!")
        print("   Some tests will be skipped.")
        print("   Set it via: export WEBHOOK_SECRET='your-secret'")
        print("   Or pass as argument: python test_webhook_auth.py <backend_url> <secret>")
    
    results = []
    
    # Test 1: Authenticated request (should succeed)
    if webhook_secret:
        results.append(("Authenticated webhook", test_authenticated_webhook(backend_url, webhook_secret)))
    
    # Test 2: Unauthenticated request (should fail)
    results.append(("Unauthenticated webhook", test_unauthenticated_webhook(backend_url)))
    
    # Test 3: Invalid signature (should fail)
    results.append(("Invalid signature", test_invalid_signature(backend_url)))
    
    # Test 4: Expired timestamp (should fail)
    if webhook_secret:
        results.append(("Expired timestamp", test_expired_timestamp(backend_url, webhook_secret)))
    
    # Test 5: Missing timestamp (should fail)
    if webhook_secret:
        results.append(("Missing timestamp", test_missing_timestamp(backend_url, webhook_secret)))
    
    # Test 6: Test endpoint in production
    results.append(("Test endpoint production check", test_test_endpoint_production(backend_url)))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Webhook authentication is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

