# HTTPS Redirect CORS Fix

## Issue

The HTTPS redirect middleware was redirecting OPTIONS requests (CORS preflight requests) from HTTP to HTTPS. This breaks CORS because:

1. Browsers send OPTIONS requests as CORS preflight before the actual request
2. CORS preflight requests must receive a direct response with CORS headers, not a redirect
3. Redirecting OPTIONS requests causes the browser to fail the CORS check, blocking the actual request

## Root Cause

The `HTTPSRedirectMiddleware` in `backend/middleware/https_redirect.py` was checking for HTTP requests and redirecting them without excluding OPTIONS requests. This meant that:

- Browser sends OPTIONS preflight request (HTTP)
- Middleware redirects to HTTPS (301)
- Browser follows redirect but CORS check fails
- Actual request is blocked

## Solution

Updated `HTTPSRedirectMiddleware` to skip redirects for OPTIONS requests:

```python
# Skip redirect for OPTIONS requests (CORS preflight)
# CORS preflight requests must be handled directly, not redirected
if request.method == "OPTIONS":
    return await call_next(request)
```

## Changes Made

1. **backend/middleware/https_redirect.py**:
   - Added check to skip OPTIONS requests before redirect logic
   - Updated docstring to document this behavior

2. **backend/tests/test_https_redirect.py**:
   - Added test case `test_no_redirect_for_options_requests` to verify OPTIONS requests are not redirected

3. **docs/deployment/HTTPS_ENFORCEMENT.md**:
   - Updated documentation to mention OPTIONS request exclusion

## Impact

- ✅ CORS preflight requests now work correctly
- ✅ HTTPS redirects still work for all other HTTP requests
- ✅ No breaking changes to existing functionality
- ✅ Better compatibility with Cloudflare hosting

## Testing

The fix includes a test case that verifies:
- OPTIONS requests are not redirected
- Other HTTP requests are still redirected to HTTPS
- CORS middleware can properly handle preflight requests

## Related Issues

This fix ensures that:
- Frontend (`https://chat.lite.space`) can make CORS requests to backend (`https://api.lite.space`)
- Admin frontend (`https://admin.lite.space`) can make CORS requests to backend
- All CORS preflight requests are handled correctly

## Date

Fixed: 2025-01-XX

