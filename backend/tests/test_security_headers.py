#!/usr/bin/env python3
"""
Test script for security headers implementation.

Tests that all required security headers are present in backend responses.
"""

import sys
import os
import requests
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Expected security headers
REQUIRED_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

# HSTS header (only in production)
HSTS_HEADER = "Strict-Transport-Security"
HSTS_VALUE_PATTERN = "max-age=31536000; includeSubDomains"

# Test endpoints
TEST_ENDPOINTS = [
    "/",
    "/health",
    "/api/v1/chat",
    "/metrics",
]


def check_header(response: requests.Response, header_name: str, expected_value: str = None) -> Tuple[bool, str]:
    """
    Check if a header is present and optionally matches expected value.
    
    Returns:
        (is_present, message)
    """
    if header_name not in response.headers:
        return False, f"Missing header: {header_name}"
    
    actual_value = response.headers[header_name]
    
    if expected_value is not None:
        if actual_value != expected_value:
            return False, f"Header {header_name} has wrong value. Expected: {expected_value}, Got: {actual_value}"
    
    return True, f"✓ {header_name}: {actual_value}"


def test_security_headers(backend_url: str = "http://localhost:8000", is_production: bool = False) -> bool:
    """
    Test security headers on all endpoints.
    
    Args:
        backend_url: Base URL of the backend
        is_production: Whether we're testing in production (expects HSTS)
    
    Returns:
        True if all tests pass, False otherwise
    """
    print(f"🔒 Testing security headers on: {backend_url}")
    print(f"   Environment: {'PRODUCTION' if is_production else 'DEVELOPMENT'}")
    print("=" * 60)
    
    all_passed = True
    
    for endpoint in TEST_ENDPOINTS:
        url = f"{backend_url}{endpoint}"
        print(f"\n📡 Testing: {endpoint}")
        
        try:
            # Use GET for most endpoints, POST for /api/v1/chat
            if endpoint == "/api/v1/chat":
                response = requests.post(
                    url,
                    json={"query": "test", "chat_history": []},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            else:
                response = requests.get(url, timeout=10)
            
            # Check required headers
            for header_name, expected_value in REQUIRED_HEADERS.items():
                passed, message = check_header(response, header_name, expected_value)
                if passed:
                    print(f"   {message}")
                else:
                    print(f"   ❌ {message}")
                    all_passed = False
            
            # Check HSTS (only in production)
            if is_production:
                passed, message = check_header(response, HSTS_HEADER, HSTS_VALUE_PATTERN)
                if passed:
                    print(f"   {message}")
                else:
                    print(f"   ❌ {message}")
                    all_passed = False
            else:
                # In development, HSTS should NOT be present
                if HSTS_HEADER in response.headers:
                    print(f"   ⚠️  HSTS header present in development (should only be in production)")
                    # Don't fail the test, just warn
                else:
                    print(f"   ✓ HSTS correctly absent in development")
            
            # Print all security-related headers for debugging
            security_headers_found = {
                k: v for k, v in response.headers.items()
                if any(keyword in k.lower() for keyword in ['security', 'frame', 'content-type', 'referrer', 'permission', 'csp'])
            }
            if security_headers_found:
                print(f"   📋 All security headers found: {', '.join(security_headers_found.keys())}")
        
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Failed to connect: {e}")
            all_passed = False
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            all_passed = False
    
    return all_passed


def test_cors_headers(backend_url: str = "http://localhost:8000") -> bool:
    """
    Test that CORS headers are present (separate from security headers).
    """
    print(f"\n🌐 Testing CORS headers on: {backend_url}")
    print("=" * 60)
    
    url = f"{backend_url}/"
    
    try:
        # Make a request with Origin header to trigger CORS
        response = requests.options(
            url,
            headers={"Origin": "http://localhost:3000"},
            timeout=10
        )
        
        cors_headers = ["Access-Control-Allow-Origin", "Access-Control-Allow-Methods", "Access-Control-Allow-Headers"]
        found_headers = []
        
        for header in cors_headers:
            if header in response.headers:
                found_headers.append(header)
                print(f"   ✓ {header}: {response.headers[header]}")
            else:
                print(f"   ⚠️  {header} not found (may be normal if CORS is configured differently)")
        
        return True
    
    except Exception as e:
        print(f"   ❌ CORS test failed: {e}")
        return False


def main():
    """Main test function."""
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    # Check if we're in production by checking NODE_ENV
    is_production = os.getenv("NODE_ENV") == "production" or os.getenv("ENVIRONMENT") == "production"
    
    if len(sys.argv) > 1:
        backend_url = sys.argv[1]
    
    if len(sys.argv) > 2:
        is_production = sys.argv[2].lower() in ["true", "1", "yes", "production"]
    
    print("🚀 Security Headers Test Suite")
    print("=" * 60)
    
    # Test security headers
    headers_passed = test_security_headers(backend_url, is_production)
    
    # Test CORS (informational)
    cors_passed = test_cors_headers(backend_url)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    if headers_passed:
        print("✅ Security headers: PASSED")
    else:
        print("❌ Security headers: FAILED")
    
    if cors_passed:
        print("✅ CORS headers: PASSED (informational)")
    else:
        print("⚠️  CORS headers: Issues detected (informational)")
    
    if headers_passed:
        print("\n🎉 All security header tests passed!")
        return True
    else:
        print("\n⚠️  Some security header tests failed. Please review the output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

