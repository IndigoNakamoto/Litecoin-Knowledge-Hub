#!/usr/bin/env python3
"""
Manual webhook testing script for debugging Payload CMS integration.
This script simulates the webhook payload that Payload CMS sends.
"""

import requests
import json
import sys
from datetime import datetime

def test_webhook_connectivity(backend_url="http://localhost:8000"):
    """Test basic connectivity to the webhook service."""
    print("🔍 Testing webhook service connectivity...")

    try:
        response = requests.get(f"{backend_url}/api/v1/sync/health", timeout=10)
        print(f"Health check response: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_webhook_payload(backend_url="http://localhost:8000"):
    """Test webhook with a sample payload."""
    print("\n🧪 Testing webhook with sample payload...")

    # Sample payload that mimics what Payload CMS sends (including markdown field)
    sample_payload = {
        "doc": {
            "id": "test-article-123",
            "title": "What is Ethereum?",
            "content": {
                "root": {
                    "type": "root",
                    "format": "",
                    "indent": 0,
                    "version": 1,
                    "children": [
                        {
                            "type": "paragraph",
                            "format": "",
                            "indent": 0,
                            "version": 1,
                            "children": [
                                {
                                    "mode": "normal",
                                    "text": "Ethereum is a decentralized blockchain platform that enables smart contracts and decentralized applications (dApps).",
                                    "type": "text",
                                    "style": "",
                                    "detail": 0,
                                    "format": 0,
                                    "version": 1
                                }
                            ],
                            "direction": "ltr",
                            "textFormat": 0,
                            "textStyle": ""
                        }
                    ],
                    "direction": "ltr",
                    "textFormat": 0,
                    "textStyle": ""
                }
            },
            "markdown": "Ethereum is a decentralized blockchain platform that enables smart contracts and decentralized applications (dApps).",
            "status": "published",
            "author": "test-user",
            "publishedDate": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }
    }

    try:
        # Test the main webhook endpoint
        print("Testing main webhook endpoint...")
        response = requests.post(
            f"{backend_url}/api/v1/sync/payload",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print(f"Webhook response: {response.status_code}")
        print(f"Response: {response.json()}")

        # Test the test endpoint
        print("\nTesting test webhook endpoint...")
        test_response = requests.post(
            f"{backend_url}/api/v1/sync/test-webhook",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"Test webhook response: {test_response.status_code}")
        print(f"Response: {test_response.json()}")

        return response.status_code == 200

    except requests.exceptions.RequestException as e:
        print(f"❌ Webhook test failed: {e}")
        return False

def main():
    """Main function to run webhook tests."""
    backend_url = "http://localhost:8000"

    if len(sys.argv) > 1:
        backend_url = sys.argv[1]

    print(f"🚀 Starting webhook tests against: {backend_url}")
    print("=" * 50)

    # Test connectivity
    connectivity_ok = test_webhook_connectivity(backend_url)

    if not connectivity_ok:
        print("\n❌ Backend service is not accessible. Please ensure:")
        print("   1. FastAPI server is running on port 8000")
        print("   2. No firewall blocking the connection")
        print("   3. Correct backend URL")
        return False

    # Test webhook functionality
    webhook_ok = test_webhook_payload(backend_url)

    if webhook_ok:
        print("\n✅ Webhook tests passed! The integration should work.")
        print("📝 Next steps:")
        print("   1. Publish an article in Payload CMS")
        print("   2. Check backend logs for processing messages")
        print("   3. Wait 30-60 seconds for background processing")
        print("   4. Test queries about the article content")
    else:
        print("\n❌ Webhook tests failed. Check the error messages above.")

    return webhook_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
