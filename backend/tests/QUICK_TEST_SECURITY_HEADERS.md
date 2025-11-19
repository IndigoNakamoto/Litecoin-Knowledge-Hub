# Quick Test: Security Headers

## Fastest Way to Test

```bash
# 1. Make sure backend is running
# 2. Run the test script
cd backend/tests
python3 test_security_headers.py
```

## Manual Quick Check

```bash
# Check backend headers
curl -I http://localhost:8000/ | grep -i "x-content-type-options\|x-frame-options\|referrer-policy\|permissions-policy"

# Should see:
# x-content-type-options: nosniff
# x-frame-options: DENY
# referrer-policy: strict-origin-when-cross-origin
# permissions-policy: geolocation=(), microphone=(), camera=()
```

## Browser Quick Check

1. Open http://localhost:8000/ in browser
2. Press F12 (DevTools)
3. Go to Network tab
4. Reload page
5. Click on any request
6. Check Response Headers for security headers

## Expected Results

✅ **All endpoints should have:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

✅ **Production only:**
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

✅ **Frontend should also have:**
- `Content-Security-Policy: ...` (comprehensive policy)

## Full Documentation

See `docs/SECURITY_HEADERS_TESTING.md` for comprehensive testing guide.

