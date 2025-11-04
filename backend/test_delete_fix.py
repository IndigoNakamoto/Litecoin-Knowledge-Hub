#!/usr/bin/env python3
"""
Test script to verify the delete webhook fix handles relationship field normalization correctly.
"""

import requests
import json
from datetime import datetime

def test_delete_webhook_fix(backend_url="http://localhost:8000"):
    """Test the delete webhook with the problematic payload format that was failing before."""

    print("🧪 Testing delete webhook fix...")

    # This is the exact payload format that was causing validation errors during deletion
    # Based on the logs: author as full object, category as list of objects
    delete_payload = {
        "operation": "delete",
        "doc": {
            "id": "test-delete-article-123",
            "title": "Test Article for Deletion",
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
                                    "text": "This is a test article that will be deleted.",
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
            "markdown": "This is a test article that will be deleted.",
            "status": "published",
            # This is the problematic format - full objects instead of strings
            "author": {
                "createdAt": "2025-11-02T20:31:29.055Z",
                "updatedAt": "2025-11-03T05:30:11.775Z",
                "roles": ["admin"],
                "authorizedLanguages": [],
                "email": "indigo@litecoin.net",
                "id": "6907bfa1b1f925b63784dc15",
                "loginAttempts": 0
            },
            "category": [
                {
                    "name": "Privacy",
                    "id": "69083e38b1f925b63784dfa9"
                }
            ],
            "publishedDate": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }
    }

    try:
        print("Sending delete webhook payload with object-format relationship fields...")
        response = requests.post(
            f"{backend_url}/api/v1/sync/payload",
            json=delete_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"Response status: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "not_published_or_deleted" and response_data.get("operation") == "delete":
                print("✅ SUCCESS: Delete operation processed correctly!")
                print("✅ Relationship field normalization worked!")
                return True
            else:
                print(f"❌ UNEXPECTED: Expected delete operation response, got: {response_data}")
                return False
        else:
            print(f"❌ FAILED: Status {response.status_code}, Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_create_webhook_still_works(backend_url="http://localhost:8000"):
    """Test that create operations still work with string-format relationship fields."""

    print("\n🧪 Testing create webhook still works...")

    # This is the normal payload format for create/update operations
    create_payload = {
        "operation": "create",
        "doc": {
            "id": "test-create-article-456",
            "title": "Test Article for Creation",
            "content": {
                "root": {
                    "type": "root",
                    "children": [
                        {
                            "type": "paragraph",
                            "children": [
                                {
                                    "text": "This is a test article that will be created.",
                                    "type": "text"
                                }
                            ]
                        }
                    ]
                }
            },
            "markdown": "This is a test article that will be created.",
            "status": "published",
            # This is the normal format - strings instead of objects
            "author": "6907bfa1b1f925b63784dc15",  # String ID
            "category": ["69083e38b1f925b63784dfa9"],  # List of string IDs
            "publishedDate": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }
    }

    try:
        print("Sending create webhook payload with string-format relationship fields...")
        response = requests.post(
            f"{backend_url}/api/v1/sync/payload",
            json=create_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"Response status: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "processing_triggered":
                print("✅ SUCCESS: Create operation processed correctly!")
                print("✅ String-format relationship fields still work!")
                return True
            else:
                print(f"❌ UNEXPECTED: Expected processing_triggered response, got: {response_data}")
                return False
        else:
            print(f"❌ FAILED: Status {response.status_code}, Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False

def main():
    """Main test function."""
    backend_url = "http://localhost:8000"

    print("🚀 Testing Payload CMS webhook delete fix")
    print("=" * 50)

    # Test delete operation with object-format fields (the problematic case)
    delete_test_passed = test_delete_webhook_fix(backend_url)

    # Test create operation with string-format fields (ensure we didn't break existing functionality)
    create_test_passed = test_create_webhook_still_works(backend_url)

    print("\n" + "=" * 50)
    if delete_test_passed and create_test_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Delete operations now handle object-format relationship fields")
        print("✅ Create operations still work with string-format relationship fields")
        print("\nThe fix is working correctly!")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        if not delete_test_passed:
            print("❌ Delete operation test failed")
        if not create_test_passed:
            print("❌ Create operation test failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
