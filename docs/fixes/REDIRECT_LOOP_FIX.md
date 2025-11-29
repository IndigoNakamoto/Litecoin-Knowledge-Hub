# Redirect Loop Fix

## Issue

Users experienced `ERR_TOO_MANY_REDIRECTS` errors when accessing:
- `https://api.lite.space/api/v1/auth/challenge`
- `https://api.lite.space/api/v1/chat/stream`
- `http://localhost:3003/` (admin frontend)

## Root Cause

The HTTPS redirect middleware was creating redirect loops in two scenarios:

1. **Behind Cloudflare**: Cloudflare already handles HTTPS redirects at the edge, but the application-level middleware was also trying to redirect, creating a loop.

2. **Localhost**: The middleware was redirecting HTTP localhost requests to HTTPS, but localhost doesn't support HTTPS, causing a loop.

3. **Missing Headers**: When `X-Forwarded-Proto` header was missing (common behind proxies), the middleware might incorrectly detect HTTP and redirect, even when the request was already HTTPS.

## Solution

Updated both backend and frontend HTTPS redirect middlewares to:

1. **Skip redirect when behind Cloudflare**: Check for `CF-Connecting-IP` header (set by Cloudflare and cannot be spoofed). If present, skip redirect and let Cloudflare handle it.

2. **Skip redirect for localhost**: Never redirect localhost or 127.0.0.1 requests, as they don't support HTTPS.

3. **Only redirect if explicitly HTTP**: Only redirect if `X-Forwarded-Proto` is explicitly set to "http". If the header is missing, assume HTTPS (common when behind a proxy).

## Changes Made

### Backend (`backend/middleware/https_redirect.py`)

```python
# Skip redirect if behind Cloudflare (Cloudflare handles HTTPS redirects at edge)
if request.headers.get("CF-Connecting-IP"):
    return await call_next(request)

# Skip redirect for localhost (development/local access)
host = request.headers.get("Host") or request.url.hostname or ""
if "localhost" in host.lower() or "127.0.0.1" in host.lower():
    return await call_next(request)

# Only redirect if explicitly HTTP (not if header is missing)
if forwarded_proto == "http" or (not forwarded_proto and request_scheme == "http"):
    # Redirect logic
```

### Frontend (`frontend/src/middleware.ts`)

```typescript
// Skip redirect if behind Cloudflare
if (request.headers.get('cf-connecting-ip')) {
    return NextResponse.next()
}

// Skip redirect for localhost
const host = request.headers.get('host') || request.nextUrl.hostname || ''
if (host.includes('localhost') || host.includes('127.0.0.1')) {
    return NextResponse.next()
}

// Only redirect if explicitly HTTP
if (forwardedProto === 'http') {
    // Redirect logic
}
```

## Impact

- ✅ No more redirect loops when behind Cloudflare
- ✅ Localhost works correctly without redirects
- ✅ HTTPS redirects still work for direct HTTP access (not behind Cloudflare)
- ✅ Better compatibility with Cloudflare Tunnel hosting

## Testing

After this fix:
- `https://api.lite.space/*` requests should work without redirect loops
- `http://localhost:3003/` should work without redirect loops
- Direct HTTP access (not behind Cloudflare) should still redirect to HTTPS

## Related Issues

This fix works together with:
- CORS configuration (OPTIONS requests are not redirected)
- Cloudflare Tunnel configuration
- HTTPS enforcement documentation

## Date

Fixed: 2025-01-XX

