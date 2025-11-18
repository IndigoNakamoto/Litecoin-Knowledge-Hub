# Webhook Security Configuration

This document describes how to configure webhook security for Payload CMS webhooks.

## Overview

The webhook endpoint (`/api/v1/sync/payload`) implements multiple security layers:

1. **HMAC Signature Verification** - Verifies webhook authenticity using a shared secret
2. **IP Allowlisting** (optional) - Restricts webhook requests to specific IP addresses
3. **Replay Attack Prevention** - Prevents reuse of old webhook requests using timestamp and nonce validation

## Configuration

### Required Environment Variables

#### `WEBHOOK_SECRET` (Required for Production)

The shared secret used for HMAC SHA-256 signature verification. This must match the secret configured in Payload CMS.

**Example:**
```bash
WEBHOOK_SECRET=your-secret-key-here-minimum-32-characters-recommended
```

**Security Notes:**
- Use a strong, randomly generated secret (minimum 32 characters recommended)
- Store this secret securely and never commit it to git
- Use different secrets for development and production environments
- Rotate secrets periodically

**Location:** Set in `backend/.env` file (not committed to git)

### Optional Environment Variables

#### `WEBHOOK_ALLOWED_IPS` (Optional)

Comma-separated list of IP addresses allowed to send webhooks. If not configured or empty, IP checking is disabled.

**Example:**
```bash
WEBHOOK_ALLOWED_IPS=203.0.113.1,198.51.100.42
```

**When to Use:**
- If you know the IP addresses of your Payload CMS instance
- For additional security layer on top of signature verification
- Leave empty if IPs are dynamic or unknown

#### `WEBHOOK_MAX_AGE` (Optional)

Maximum age of webhook requests in seconds. Requests older than this will be rejected to prevent replay attacks.

**Default:** 300 seconds (5 minutes)

**Example:**
```bash
WEBHOOK_MAX_AGE=300
```

## Payload CMS Configuration

To enable webhook security, you need to configure Payload CMS to sign webhooks with the shared secret.

### 1. Generate a Secret

Generate a strong, random secret:

```bash
# Using openssl
openssl rand -hex 32

# Or using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Configure Payload CMS

In your Payload CMS configuration, add the webhook secret to your webhook endpoint configuration.

**Example Payload CMS webhook configuration:**
```javascript
// In payload.config.ts or similar
webhooks: [
  {
    url: 'http://backend:8000/api/v1/sync/payload',
    secret: process.env.WEBHOOK_SECRET, // Must match backend WEBHOOK_SECRET
    events: ['afterChange'],
  }
]
```

### 3. Configure Payload CMS to Sign Webhooks

Payload CMS should sign webhooks using HMAC SHA-256 with the shared secret.

**Signature Header:** `X-Payload-Signature` or `X-Webhook-Signature`

**Signature Calculation:**
```python
import hmac
import hashlib

def calculate_signature(payload_body: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
```

**Payload Format:**
The webhook payload should include:
- `timestamp` (Unix timestamp) - For replay attack prevention
- `nonce` or `id` (unique identifier) - For duplicate request prevention
- `doc` (document data) - The actual payload data

## Security Best Practices

1. **Always use webhook security in production**
   - Never leave `WEBHOOK_SECRET` unconfigured in production
   - Production endpoints without authentication are vulnerable to content injection

2. **Use strong secrets**
   - Minimum 32 characters
   - Randomly generated
   - Different secrets for different environments

3. **Enable IP allowlisting if possible**
   - Adds an additional security layer
   - Helps prevent attacks even if secret is compromised

4. **Monitor webhook failures**
   - Check logs for failed webhook verifications
   - Alert on repeated authentication failures (possible attack)

5. **Rotate secrets periodically**
   - Change secrets every 90 days or after any security incident
   - Update both Payload CMS and backend simultaneously

## Testing

### Test Webhook Endpoint

The `/api/v1/sync/test-webhook` endpoint allows testing webhook payloads without authentication. This endpoint:
- Does NOT require webhook authentication (for testing purposes only)
- Validates payload structure
- Can be used for development and debugging

**Note:** This endpoint should be disabled or restricted in production.

### Development Mode

If `WEBHOOK_SECRET` is not configured, webhook security is disabled and all requests are allowed. This is useful for development but **must not be used in production**.

## Troubleshooting

### Webhook Verification Failing

**Check:**
1. Verify `WEBHOOK_SECRET` matches between Payload CMS and backend
2. Ensure Payload CMS is sending the `X-Payload-Signature` or `X-Webhook-Signature` header
3. Verify the signature is calculated correctly (HMAC SHA-256)
4. Check webhook payload includes `timestamp` and `nonce` fields

**Common Issues:**
- **Invalid signature**: Secret mismatch or incorrect signature calculation
- **Unauthorized IP**: Client IP not in `WEBHOOK_ALLOWED_IPS` list
- **Invalid timestamp**: Webhook too old or timestamp missing
- **Nonce reused**: Same webhook sent multiple times

### Logs

Check application logs for webhook security events:

```bash
# View webhook authentication failures
docker logs litecoin-backend | grep -i "webhook.*rejected"

# View successful webhook verifications
docker logs litecoin-backend | grep -i "webhook.*verified"
```

## Migration Guide

### Enabling Webhook Security on Existing Deployment

1. **Generate a secret:**
   ```bash
   openssl rand -hex 32
   ```

2. **Update `backend/.env`:**
   ```bash
   WEBHOOK_SECRET=your-generated-secret-here
   ```

3. **Update Payload CMS configuration:**
   - Add webhook secret to Payload CMS config
   - Ensure Payload CMS signs webhooks with HMAC SHA-256

4. **Restart services:**
   ```bash
   docker-compose -f docker-compose.prod.yml restart backend
   ```

5. **Test webhook:**
   - Trigger a webhook from Payload CMS
   - Verify it's accepted and processed

6. **Monitor logs:**
   - Check for any authentication failures
   - Verify webhooks are being processed successfully

