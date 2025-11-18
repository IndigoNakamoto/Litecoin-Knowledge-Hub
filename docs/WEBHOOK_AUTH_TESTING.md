# Webhook Authentication Testing Guide

This guide explains how to test the webhook authentication implementation (CRIT-1 fix).

## Overview

The webhook endpoint `/api/v1/sync/payload` now requires:
- **HMAC-SHA256 signature** in `X-Webhook-Signature` header
- **Unix timestamp** in `X-Webhook-Timestamp` header (within 5 minutes)

## Prerequisites

1. **Set up WEBHOOK_SECRET** in both services:
   ```bash
   # Generate a secret
   export WEBHOOK_SECRET=$(openssl rand -base64 32)
   
   # Add to backend/.env
   echo "WEBHOOK_SECRET=$WEBHOOK_SECRET" >> backend/.env
   
   # Add to payload_cms/.env
   echo "WEBHOOK_SECRET=$WEBHOOK_SECRET" >> payload_cms/.env
   ```

2. **Start the services**:
   ```bash
   # Backend
   cd backend
   uvicorn main:app --reload
   
   # Payload CMS (in another terminal)
   cd payload_cms
   npm run dev
   ```

## Automated Testing

### Run the Test Suite

```bash
cd backend/tests
python test_webhook_auth.py
```

Or with custom backend URL and secret:
```bash
python test_webhook_auth.py http://localhost:8000 your-secret-here
```

The test suite covers:
- ✅ Authenticated requests (should succeed)
- ❌ Unauthenticated requests (should fail with 401)
- ❌ Invalid signatures (should fail with 401)
- ❌ Expired timestamps (should fail with 401)
- ❌ Missing headers (should fail with 401)
- 🔒 Test endpoint in production (should be disabled)

## Manual Testing with cURL

### 1. Test Authenticated Request (Should Succeed)

```bash
# Set your secret
export WEBHOOK_SECRET="your-secret-here"

# Create payload
PAYLOAD='{"operation":"create","doc":{"id":"test-123","title":"Test Article","status":"published"}}'

# Generate signature
TIMESTAMP=$(date +%s)
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | cut -d' ' -f2)

# Send request
curl -X POST http://localhost:8000/api/v1/sync/payload \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: $SIGNATURE" \
  -H "X-Webhook-Timestamp: $TIMESTAMP" \
  -d "$PAYLOAD"
```

**Expected:** Status 200 with success response

### 2. Test Unauthenticated Request (Should Fail)

```bash
curl -X POST http://localhost:8000/api/v1/sync/payload \
  -H "Content-Type: application/json" \
  -d '{"operation":"create","doc":{"id":"test-123","title":"Test Article","status":"published"}}'
```

**Expected:** Status 401 with error message

### 3. Test Invalid Signature (Should Fail)

```bash
TIMESTAMP=$(date +%s)
curl -X POST http://localhost:8000/api/v1/sync/payload \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: invalid_signature" \
  -H "X-Webhook-Timestamp: $TIMESTAMP" \
  -d '{"operation":"create","doc":{"id":"test-123","title":"Test Article","status":"published"}}'
```

**Expected:** Status 401 with error message

### 4. Test Expired Timestamp (Should Fail)

```bash
export WEBHOOK_SECRET="your-secret-here"
PAYLOAD='{"operation":"create","doc":{"id":"test-123","title":"Test Article","status":"published"}}'

# Use timestamp from 10 minutes ago
EXPIRED_TIMESTAMP=$(($(date +%s) - 600))
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | cut -d' ' -f2)

curl -X POST http://localhost:8000/api/v1/sync/payload \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: $SIGNATURE" \
  -H "X-Webhook-Timestamp: $EXPIRED_TIMESTAMP" \
  -d "$PAYLOAD"
```

**Expected:** Status 401 with error message

## Testing with Python Script

Create a simple test script:

```python
import requests
import hmac
import hashlib
import time
import json
import os

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-secret-here")
BACKEND_URL = "http://localhost:8000"

# Create payload
payload = {
    "operation": "create",
    "doc": {
        "id": "test-python-123",
        "title": "Test from Python",
        "status": "published"
    }
}

payload_str = json.dumps(payload)
timestamp = str(int(time.time()))

# Generate signature
signature = hmac.new(
    WEBHOOK_SECRET.encode('utf-8'),
    payload_str.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# Send request
headers = {
    "Content-Type": "application/json",
    "X-Webhook-Signature": signature,
    "X-Webhook-Timestamp": timestamp
}

response = requests.post(
    f"{BACKEND_URL}/api/v1/sync/payload",
    data=payload_str,
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

## Testing from Payload CMS

### 1. Verify WEBHOOK_SECRET is Set

Check that `payload_cms/.env` contains:
```
WEBHOOK_SECRET=your-secret-here
```

And `backend/.env` contains the same value:
```
WEBHOOK_SECRET=your-secret-here
```

### 2. Test Webhook Trigger

1. Open Payload CMS admin panel
2. Create or update an article
3. Check backend logs for webhook processing
4. Verify the webhook succeeds (not 401)

### 3. Check Backend Logs

```bash
# Watch backend logs
tail -f backend/logs/app.log

# Or if using uvicorn directly
# You should see webhook processing logs
```

Look for:
- ✅ "Received Payload webhook" - webhook received
- ✅ "Processing triggered" - authentication passed
- ❌ "Webhook authentication failed" - authentication failed

## Testing Test Endpoint

### Development Mode

```bash
# Should work (if WEBHOOK_SECRET not set) or require auth (if set)
curl -X POST http://localhost:8000/api/v1/sync/test-webhook \
  -H "Content-Type: application/json" \
  -d '{"doc":{"id":"test","title":"Test","status":"published"}}'
```

### Production Mode

```bash
# Set NODE_ENV=production
export NODE_ENV=production

# Restart backend, then test
curl -X POST http://localhost:8000/api/v1/sync/test-webhook \
  -H "Content-Type: application/json" \
  -d '{"doc":{"id":"test","title":"Test","status":"published"}}'
```

**Expected:** Status 404 (endpoint disabled in production)

## Troubleshooting

### Issue: All requests return 401

**Check:**
1. `WEBHOOK_SECRET` is set in both `backend/.env` and `payload_cms/.env`
2. The secret values are **exactly the same** in both files
3. Backend has been restarted after adding `WEBHOOK_SECRET`

### Issue: Signature verification fails

**Check:**
1. Payload is serialized the same way (JSON with no extra spaces)
2. Signature is computed on the exact payload bytes
3. Secret is correct and matches between services

### Issue: Timestamp validation fails

**Check:**
1. System clocks are synchronized (within 5 minutes)
2. Timestamp is Unix timestamp (seconds since epoch)
3. Timestamp is sent as string in header

### Issue: Test endpoint not working

**Check:**
1. `NODE_ENV` is not set to "production" (for development testing)
2. If `WEBHOOK_SECRET` is set, test endpoint requires authentication
3. In production, test endpoint is intentionally disabled

## Verification Checklist

- [ ] Automated test suite passes
- [ ] Authenticated requests succeed
- [ ] Unauthenticated requests fail with 401
- [ ] Invalid signatures are rejected
- [ ] Expired timestamps are rejected
- [ ] Payload CMS webhooks work correctly
- [ ] Test endpoint is disabled in production
- [ ] Backend logs show authentication success/failure appropriately

## Security Notes

1. **Never commit WEBHOOK_SECRET** to version control
2. **Use different secrets** for development and production
3. **Rotate secrets** periodically
4. **Monitor logs** for authentication failures (potential attacks)
5. **Keep timestamps synchronized** between services

## Next Steps

After verifying webhook authentication works:
1. Test with real Payload CMS integration
2. Monitor logs for any authentication issues
3. Set up alerts for repeated authentication failures
4. Document the secret rotation process

