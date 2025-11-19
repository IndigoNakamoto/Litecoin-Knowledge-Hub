# CRIT-8 Fix Plan: Permissive CORS Configuration

## Overview

This document outlines the plan to fix **CRIT-8: Permissive CORS Configuration** and **HIGH-NEW-1: Hardcoded CORS Wildcard in Streaming Endpoint**. These issues create security vulnerabilities that enable CSRF attacks and unauthorized API access.

## Current Issues

### Issue 1: Permissive CORS Middleware (CRIT-8)
**Location:** `backend/main.py:162-168`

**Current Configuration:**
```python
app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins,  # ✅ Correctly configured from env var
    allow_credentials=True,  # ⚠️ May not be needed
    allow_methods=["*"],     # ❌ Too permissive
    allow_headers=["*"],     # ❌ Too permissive
)
```

**Problems:**
- `allow_methods=["*"]` allows all HTTP methods (PUT, DELETE, PATCH, etc.) even though only GET and POST are used
- `allow_headers=["*"]` allows any custom headers, increasing attack surface
- `allow_credentials=True` may not be necessary (no cookie-based auth currently)

### Issue 2: Hardcoded CORS Wildcard in Streaming Endpoint (HIGH-NEW-1)
**Location:** `backend/main.py:415-424`

**Current Configuration:**
```python
return StreamingResponse(
    generate_stream(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",  # ❌ Bypasses CORS middleware
        "Access-Control-Allow-Headers": "Cache-Control",  # ❌ Incomplete
    }
)
```

**Problems:**
- Hardcoded `Access-Control-Allow-Origin: *` bypasses the CORS middleware
- Allows requests from any origin (including malicious websites)
- Creates inconsistency with other endpoints
- Missing required headers for proper CORS (e.g., `Access-Control-Allow-Methods`)

## Required Headers Analysis

### Frontend Request Headers
Based on code review, the frontend sends:
1. **Chat/Stream endpoints:**
   - `Content-Type: application/json`
   - No custom headers

2. **Authenticated endpoints (ArticleEditor):**
   - `Content-Type: application/json`
   - `Authorization: Bearer <token>`

3. **Server-Sent Events (Streaming):**
   - Browser automatically sends `Cache-Control` header for SSE
   - No custom headers required

### Required HTTP Methods
- `GET` - For health checks, metrics, root endpoint
- `POST` - For chat, stream, webhook endpoints
- `OPTIONS` - For CORS preflight requests (handled automatically by middleware)

### Required CORS Headers
- `Content-Type` - Required for JSON requests
- `Authorization` - Required for authenticated endpoints
- `Cache-Control` - Used by browser for SSE connections (optional but safe to allow)

## Implementation Plan

### Step 1: Fix CORS Middleware Configuration

**File:** `backend/main.py`

**Changes:**
1. Restrict `allow_methods` to only required methods: `["GET", "POST", "OPTIONS"]`
2. Restrict `allow_headers` to only required headers: `["Content-Type", "Authorization", "Cache-Control"]`
3. Keep `allow_credentials=True` for future-proofing (even though not currently used)
4. Keep `allow_origins=origins` (already correctly configured from `CORS_ORIGINS` env var)

**New Configuration:**
```python
app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins,  # From CORS_ORIGINS env var
    allow_credentials=True,  # Keep for future cookie-based auth
    allow_methods=["GET", "POST", "OPTIONS"],  # Only required methods
    allow_headers=["Content-Type", "Authorization", "Cache-Control"],  # Only required headers
)
```

### Step 2: Remove Hardcoded CORS Headers from Streaming Endpoint

**File:** `backend/main.py`

**Changes:**
1. Remove hardcoded `Access-Control-Allow-Origin: *` header
2. Remove hardcoded `Access-Control-Allow-Headers: Cache-Control` header
3. Let CORS middleware handle all CORS headers consistently
4. Keep only non-CORS headers (`Cache-Control`, `Connection`)

**New Configuration:**
```python
return StreamingResponse(
    generate_stream(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # CORS headers handled by middleware - removed hardcoded wildcards
    }
)
```

### Step 3: Verify CORS_ORIGINS Environment Variable

**Check:** Ensure `CORS_ORIGINS` is properly configured in all environments:

**Development:**
- `CORS_ORIGINS=http://localhost:3000`

**Production:**
- `CORS_ORIGINS=https://chat.lite.space,https://cms.lite.space`

**Note:** The middleware already correctly parses comma-separated origins from the env var.

### Step 4: Testing Plan

#### Test 1: Verify CORS Middleware Works
- Test that allowed origins can make requests
- Test that disallowed origins are blocked
- Test preflight OPTIONS requests

#### Test 2: Verify Streaming Endpoint CORS
- Test that streaming endpoint respects CORS middleware
- Test that hardcoded wildcard is removed
- Test that SSE connections work from allowed origins

#### Test 3: Verify Required Headers Work
- Test `Content-Type: application/json` header is allowed
- Test `Authorization: Bearer <token>` header is allowed
- Test that unauthorized headers are blocked

#### Test 4: Verify Required Methods Work
- Test GET requests work
- Test POST requests work
- Test that unauthorized methods (PUT, DELETE) are blocked

## Security Impact

### Before Fix:
- ❌ Any origin can make requests (streaming endpoint)
- ❌ Any HTTP method allowed
- ❌ Any header allowed
- ❌ CSRF vulnerability for future authenticated endpoints
- ❌ Inconsistent CORS handling

### After Fix:
- ✅ Only allowed origins can make requests
- ✅ Only required HTTP methods allowed
- ✅ Only required headers allowed
- ✅ CSRF protection for authenticated endpoints
- ✅ Consistent CORS handling across all endpoints

## Risk Assessment

### Risk Level: **LOW** (for implementation)
- Changes are straightforward and well-defined
- CORS middleware is well-tested in FastAPI
- No breaking changes to existing functionality

### Rollback Plan:
If issues occur, revert to previous configuration:
```python
# Temporary rollback (not recommended for production)
allow_methods=["*"],
allow_headers=["*"],
```

## Implementation Checklist

- [ ] Update CORS middleware configuration in `backend/main.py`
  - [ ] Restrict `allow_methods` to `["GET", "POST", "OPTIONS"]`
  - [ ] Restrict `allow_headers` to `["Content-Type", "Authorization", "Cache-Control"]`
- [ ] Remove hardcoded CORS headers from streaming endpoint
  - [ ] Remove `Access-Control-Allow-Origin: *`
  - [ ] Remove `Access-Control-Allow-Headers: Cache-Control`
- [ ] Test CORS configuration in development
  - [ ] Test allowed origins work
  - [ ] Test disallowed origins are blocked
  - [ ] Test streaming endpoint CORS
  - [ ] Test authenticated endpoints
- [ ] Test CORS configuration in production
  - [ ] Verify production origins work
  - [ ] Verify no regressions
- [ ] Update documentation if needed
- [ ] Mark CRIT-8 and HIGH-NEW-1 as resolved in security assessment

## Estimated Effort

- **Implementation:** 30-60 minutes
- **Testing:** 30-60 minutes
- **Total:** 1-2 hours

## Related Issues

- **CRIT-8:** Permissive CORS Configuration (this issue)
- **HIGH-NEW-1:** Hardcoded CORS Wildcard in Streaming Endpoint (related issue, fixed together)

## References

- [FastAPI CORS Middleware Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [OWASP CORS Security Guide](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html#cross-origin-resource-sharing)
- Red Team Assessment: `docs/RED_TEAM_ASSESSMENT_COMBINED.md`

