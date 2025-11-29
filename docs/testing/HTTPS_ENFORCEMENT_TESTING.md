# HTTPS Enforcement Testing Guide

## Overview

This guide describes how to test HTTPS enforcement for the Litecoin Knowledge Hub application. HTTPS enforcement includes:

1. HTTP to HTTPS redirects
2. HSTS (Strict-Transport-Security) headers
3. Security headers (X-Frame-Options, CSP, etc.)
4. TLS certificate validation

## Automated Tests

### Backend Middleware Tests

Run the automated tests for HTTPS redirect middleware:

```bash
# Test HTTPS redirect middleware
python -m pytest backend/tests/test_https_redirect.py -v

# Test HSTS headers
python -m pytest backend/tests/test_security_headers_hsts.py -v
```

**Expected Results:**
- All tests should pass
- Tests verify:
  - HTTP requests redirect to HTTPS in production
  - No redirects in development mode
  - Health check endpoints are excluded from redirects
  - Query parameters are preserved in redirects
  - HSTS headers are added in production only

### Verification Script

Use the verification script to test HTTPS enforcement on a live deployment:

```bash
# Test frontend
./scripts/verify-https-enforcement.sh https://chat.lite.space

# Test backend API
./scripts/verify-https-enforcement.sh https://api.lite.space
```

**What it checks:**
- ✓ HTTPS URL accessibility
- ✓ TLS certificate validity
- ✓ HSTS header presence and configuration
- ✓ Security headers (X-Frame-Options, CSP, etc.)
- ✓ HTTP to HTTPS redirect
- ✓ Cloudflare integration (if applicable)

## Manual Testing

### 1. Test HTTP to HTTPS Redirect

#### Using curl:

```bash
# Test frontend redirect
curl -I http://chat.lite.space

# Should return:
# HTTP/1.1 301 Moved Permanently
# Location: https://chat.lite.space

# Test backend redirect
curl -I http://api.lite.space/api/v1/chat/stream

# Should return:
# HTTP/1.1 301 Moved Permanently
# Location: https://api.lite.space/api/v1/chat/stream
```

#### Using browser:

1. Open browser developer tools (F12)
2. Navigate to `http://chat.lite.space` (note: HTTP, not HTTPS)
3. Check Network tab - should see 301 redirect to HTTPS
4. Final URL should be `https://chat.lite.space`

### 2. Test HSTS Header

```bash
# Check HSTS header
curl -I https://chat.lite.space | grep -i strict-transport-security

# Expected output:
# Strict-Transport-Security: max-age=31536000; includeSubDomains
```

**Verify:**
- Header is present
- `max-age` is at least 31536000 (1 year)
- `includeSubDomains` directive is present

### 3. Test Security Headers

```bash
# Get all headers
curl -I https://chat.lite.space

# Should include:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# Content-Security-Policy: ...
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# Referrer-Policy: strict-origin-when-cross-origin
# Permissions-Policy: geolocation=(), microphone=(), camera=()
```

### 4. Test Health Check Endpoints (Should NOT Redirect)

Health check endpoints should be accessible via HTTP (for monitoring):

```bash
# Backend health check (should work via HTTP)
curl http://api.lite.space/health

# Should return 200 OK (not redirect)
# Note: This may still redirect if Cloudflare "Always Use HTTPS" is enabled
# In that case, use direct container access or internal network
```

### 5. Test Development Mode (Should NOT Redirect)

In development mode, HTTP requests should NOT redirect:

```bash
# Set development mode
export NODE_ENV=development

# Start backend
cd backend && python -m uvicorn main:app --reload

# Test HTTP request (should work, no redirect)
curl http://localhost:8000/api/v1/chat/stream

# Should return 200 OK or appropriate response (not 301 redirect)
```

## Testing with Cloudflare

### Verify Cloudflare Configuration

1. **Check "Always Use HTTPS" is enabled:**
   - Log in to Cloudflare Dashboard
   - Go to SSL/TLS → Edge Certificates
   - Verify "Always Use HTTPS" toggle is ON

2. **Verify TLS Mode:**
   - SSL/TLS encryption mode should be "Full" or "Full (strict)"
   - This ensures end-to-end encryption

3. **Test Cloudflare Headers:**
   ```bash
   curl -I https://chat.lite.space | grep -i cf-
   
   # Should show Cloudflare headers like:
   # CF-Ray: ...
   # CF-Cache-Status: ...
   ```

### Test Edge-Level Redirect

Cloudflare should redirect HTTP to HTTPS before requests reach the application:

```bash
# Test edge redirect (before application)
curl -I http://chat.lite.space

# Should return 301 redirect from Cloudflare
# Location: https://chat.lite.space
```

## Integration Testing

### Test Full Request Flow

1. **Start production environment:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Test HTTP request:**
   ```bash
   # Should redirect to HTTPS
   curl -L http://localhost:3000
   ```

3. **Test HTTPS request:**
   ```bash
   # Should work normally
   curl https://localhost:3000
   ```

4. **Verify headers:**
   ```bash
   curl -I https://localhost:3000 | grep -i strict-transport-security
   ```

## Browser Testing

### Chrome/Edge DevTools

1. Open DevTools (F12)
2. Go to Network tab
3. Navigate to `http://chat.lite.space`
4. Check:
   - First request should be HTTP (301 redirect)
   - Second request should be HTTPS (200 OK)
   - Response headers should include HSTS

### Security Headers Check

Use online tools to verify security headers:

- [SecurityHeaders.com](https://securityheaders.com/)
- [Mozilla Observatory](https://observatory.mozilla.org/)

Enter your domain and check:
- HSTS header is present
- Security headers are configured correctly
- Overall security score

## Troubleshooting

### Issue: HTTP requests not redirecting

**Check:**
1. Is application running in production mode? (`NODE_ENV=production`)
2. Is Cloudflare "Always Use HTTPS" enabled?
3. Is middleware registered correctly in `backend/main.py`?
4. Check application logs for redirect messages

**Debug:**
```bash
# Check environment
echo $NODE_ENV

# Check middleware registration
grep -n "HTTPSRedirectMiddleware" backend/main.py

# Check logs
docker logs litecoin-backend | grep -i redirect
```

### Issue: HSTS header missing

**Check:**
1. Is application running in production mode?
2. Is SecurityHeadersMiddleware registered?
3. Are headers being stripped by reverse proxy?

**Debug:**
```bash
# Check headers
curl -I https://chat.lite.space

# Check middleware
grep -n "SecurityHeadersMiddleware" backend/main.py

# Check environment
echo $NODE_ENV
```

### Issue: Health checks redirecting

**Solution:**
Health check endpoints are excluded from redirects in the middleware. If they still redirect:
1. Check Cloudflare "Always Use HTTPS" setting
2. Use direct container access for health checks
3. Verify exclude_paths in HTTPSRedirectMiddleware

## Test Checklist

Before deploying to production, verify:

- [ ] Backend middleware tests pass
- [ ] HSTS header tests pass
- [ ] Verification script runs successfully
- [ ] HTTP requests redirect to HTTPS
- [ ] HSTS header is present with correct values
- [ ] Security headers are present
- [ ] Health check endpoints work (may need direct access)
- [ ] Development mode does not redirect
- [ ] Cloudflare "Always Use HTTPS" is enabled
- [ ] TLS certificate is valid

## References

- [HTTPS Enforcement Documentation](../deployment/HTTPS_ENFORCEMENT.md)
- [Security Assessment](../security/RED_TEAM_ASSESSMENT_REVISED_2025.md)
- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

