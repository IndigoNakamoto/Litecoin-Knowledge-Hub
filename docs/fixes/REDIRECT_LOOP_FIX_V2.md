# Redirect Loop Fix V2 - Cloudflare Environment Variable

## Issue

Even after the initial fix, redirect loops were still occurring when accessing `https://api.lite.space/*` endpoints. The `CF-Connecting-IP` header detection wasn't sufficient in all cases.

## Root Cause

When behind Cloudflare Tunnel, the `CF-Connecting-IP` header might not always be present or reliably detected, causing the middleware to still attempt redirects and create loops.

## Solution

Added an environment variable `BEHIND_CLOUDFLARE` that can be set to explicitly disable HTTPS redirects when behind Cloudflare. This provides a more reliable way to disable application-level redirects.

### Changes Made

1. **backend/middleware/https_redirect.py**:
   - Added `BEHIND_CLOUDFLARE` environment variable check
   - If set to `true`, the middleware completely skips redirects
   - This works in addition to the `CF-Connecting-IP` header detection

2. **docker-compose.prod.yml**:
   - Added `BEHIND_CLOUDFLARE=true` to backend environment variables
   - This ensures redirects are disabled when running behind Cloudflare

## Configuration

### Environment Variable

Set `BEHIND_CLOUDFLARE=true` in your production environment:

```bash
# In .env.docker.prod or docker-compose.prod.yml
BEHIND_CLOUDFLARE=true
```

### How It Works

1. **With BEHIND_CLOUDFLARE=true**: Middleware completely skips all redirect logic when this is set
2. **With CF-Connecting-IP header**: Middleware also skips redirects if this Cloudflare header is detected
3. **Fallback**: If neither is present, middleware uses normal redirect logic (for non-Cloudflare deployments)

## Impact

- ✅ Completely prevents redirect loops when behind Cloudflare
- ✅ Can be explicitly configured via environment variable
- ✅ Still works with header-based detection as fallback
- ✅ No breaking changes for non-Cloudflare deployments

## Testing

After setting `BEHIND_CLOUDFLARE=true` and rebuilding:
- `https://api.lite.space/api/v1/auth/challenge` should work without redirect loops
- `https://api.lite.space/api/v1/admin/auth/verify` should work without redirect loops
- All HTTPS requests should proceed normally

## Date

Fixed: 2025-01-XX

