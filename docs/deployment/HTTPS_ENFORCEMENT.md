# HTTPS Enforcement Configuration

## Overview

This document describes the HTTPS enforcement configuration for the Litecoin Knowledge Hub application. HTTPS enforcement is critical for security and is required for production deployments.

## Architecture

The application uses a multi-layered approach to HTTPS enforcement:

1. **Cloudflare Tunnel (Primary)** - Handles TLS termination and edge-level redirects
2. **Application-Level Redirects (Defense-in-Depth)** - Backend and frontend redirect HTTP to HTTPS
3. **HSTS Headers** - Instruct browsers to always use HTTPS

## Components

### 1. Cloudflare Tunnel Configuration

The application uses Cloudflare Tunnel (cloudflared) for TLS termination. This is configured in `docker-compose.prod.yml`:

```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  container_name: litecoin-cloudflared
  command: tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
```

**Required Cloudflare Dashboard Settings:**

1. **Enable "Always Use HTTPS"**:
   - Go to Cloudflare Dashboard → SSL/TLS → Edge Certificates
   - Enable "Always Use HTTPS" toggle
   - This redirects all HTTP traffic to HTTPS at the edge

2. **Verify TLS Mode**:
   - SSL/TLS encryption mode should be set to "Full" or "Full (strict)"
   - This ensures end-to-end encryption

3. **Verify Tunnel Configuration**:
   - Ensure tunnel is properly configured in Cloudflare Zero Trust dashboard
   - Verify tunnel token is set in `CLOUDFLARE_TUNNEL_TOKEN` environment variable

### 2. Backend HTTPS Redirect Middleware

Location: `backend/middleware/https_redirect.py`

The backend includes middleware that redirects HTTP requests to HTTPS in production:

- **Environment Detection**: Only redirects when `NODE_ENV=production` or `ENVIRONMENT=production`
- **Header Detection**: Checks `X-Forwarded-Proto` header (set by Cloudflare) to detect HTTP requests
- **Excluded Paths**: Health checks (`/`, `/health`, `/health/live`, `/health/ready`, `/metrics`) are excluded from redirects
- **Status Code**: Uses 301 (Permanent Redirect)

**Implementation Details:**
- Middleware is registered in `backend/main.py` before security headers middleware
- Preserves query parameters and path during redirect
- Logs redirects for monitoring

### 3. Frontend HTTPS Redirect Middleware

Location: `frontend/src/middleware.ts`

The frontend (Next.js) includes middleware that redirects HTTP requests to HTTPS:

- **Environment Detection**: Only redirects when `NODE_ENV=production`
- **Header Detection**: Checks `X-Forwarded-Proto` header to detect HTTP requests
- **Route Matching**: Applies to all routes except static files and API routes
- **Status Code**: Uses 301 (Permanent Redirect)

### 4. HSTS Headers

**Backend**: `backend/middleware/security_headers.py`
- Adds `Strict-Transport-Security: max-age=31536000; includeSubDomains` in production
- Max-age is 1 year (31536000 seconds)
- Includes `includeSubDomains` directive

**Frontend**: `frontend/next.config.ts`
- Adds `Strict-Transport-Security: max-age=31536000; includeSubDomains` in production
- Configured via Next.js headers() function

## Verification

### Automated Verification Script

Use the verification script to test HTTPS enforcement:

```bash
./scripts/verify-https-enforcement.sh [BASE_URL]
```

**Example:**
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

### Manual Verification

1. **Test HTTP Redirect**:
   ```bash
   curl -I http://chat.lite.space
   # Should return 301 redirect to https://
   ```

2. **Test HSTS Header**:
   ```bash
   curl -I https://chat.lite.space | grep -i strict-transport-security
   # Should return: Strict-Transport-Security: max-age=31536000; includeSubDomains
   ```

3. **Test Security Headers**:
   ```bash
   curl -I https://chat.lite.space
   # Should include:
   # - X-Frame-Options: DENY
   # - X-Content-Type-Options: nosniff
   # - Content-Security-Policy: ...
   # - Strict-Transport-Security: ...
   ```

## Environment Variables

No additional environment variables are required for HTTPS enforcement. The middleware automatically detects production environment via:
- `NODE_ENV=production`
- `ENVIRONMENT=production`

## Troubleshooting

### Issue: HTTP requests not redirecting

**Possible Causes:**
1. Cloudflare "Always Use HTTPS" not enabled
2. Application not running in production mode
3. Middleware not registered correctly

**Solutions:**
1. Verify Cloudflare dashboard settings
2. Check environment variables: `echo $NODE_ENV`
3. Verify middleware is registered in `backend/main.py` and `frontend/src/middleware.ts`

### Issue: HSTS header missing

**Possible Causes:**
1. Not running in production mode
2. Security headers middleware not registered
3. Headers being stripped by reverse proxy

**Solutions:**
1. Verify `NODE_ENV=production` or `ENVIRONMENT=production`
2. Check middleware registration in `backend/main.py` and `frontend/next.config.ts`
3. Verify Cloudflare is not stripping headers (check Cloudflare dashboard)

### Issue: Health checks redirecting

**Possible Causes:**
1. Health check paths not in exclude list
2. Middleware order issue

**Solutions:**
1. Verify health check paths are excluded in `HTTPSRedirectMiddleware.exclude_paths`
2. Health checks should use direct container access (not through Cloudflare)

## Security Assessment

This implementation addresses **HIGH-7: HTTPS Enforcement Verification** from the security assessment:

- ✅ TLS termination handled by Cloudflare Tunnel
- ✅ HSTS headers configured and verified
- ✅ HTTP to HTTPS redirects implemented (edge and application level)
- ✅ Verification script created for ongoing monitoring

## References

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Next.js Middleware Documentation](https://nextjs.org/docs/app/building-your-application/routing/middleware)
- [FastAPI Middleware Documentation](https://fastapi.tiangolo.com/advanced/middleware/)
- [HSTS Specification](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security)

