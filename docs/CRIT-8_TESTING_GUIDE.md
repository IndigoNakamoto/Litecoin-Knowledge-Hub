# CRIT-8 CORS Testing Guide

This guide provides step-by-step instructions to test the CORS configuration fixes.

## Prerequisites

- Backend server running on `http://localhost:8000`
- Frontend server running on `http://localhost:3000` (optional, for full integration test)
- `curl` command available (or use browser DevTools)

## Test 1: Verify CORS Preflight (OPTIONS) Request

### Test 1a: Allowed Origin (Should Succeed)

```bash
curl -X OPTIONS http://localhost:8000/api/v1/chat \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

**Expected Result:**
- ✅ Status: `200 OK` or `204 No Content`
- ✅ Header: `Access-Control-Allow-Origin: http://localhost:3000`
- ✅ Header: `Access-Control-Allow-Methods: GET, POST, OPTIONS`
- ✅ Header: `Access-Control-Allow-Headers: Content-Type, Authorization, Cache-Control`
- ✅ Header: `Access-Control-Allow-Credentials: true`

### Test 1b: Disallowed Origin (Should Fail)

```bash
curl -X OPTIONS http://localhost:8000/api/v1/chat \
  -H "Origin: http://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

**Expected Result:**
- ❌ Status: `200 OK` (preflight can succeed, but actual request will fail)
- ❌ Header: `Access-Control-Allow-Origin` should be missing or not match `http://evil.com`

## Test 2: Verify Actual POST Request with CORS

### Test 2a: Allowed Origin (Should Succeed)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Litecoin?", "chat_history": []}' \
  -v
```

**Expected Result:**
- ✅ Status: `200 OK` (or rate limit error if exceeded)
- ✅ Header: `Access-Control-Allow-Origin: http://localhost:3000`
- ✅ Response body contains chat response

### Test 2b: Disallowed Origin (Should Fail)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Origin: http://evil.com" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Litecoin?", "chat_history": []}' \
  -v
```

**Expected Result:**
- ⚠️ Status: May be `200 OK` (server processes request)
- ❌ Header: `Access-Control-Allow-Origin` should NOT be `http://evil.com`
- ❌ Browser will block the response due to CORS policy

## Test 3: Verify Streaming Endpoint CORS

### Test 3a: Allowed Origin (Should Succeed)

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Litecoin?", "chat_history": []}' \
  -v --no-buffer
```

**Expected Result:**
- ✅ Status: `200 OK`
- ✅ Header: `Access-Control-Allow-Origin: http://localhost:3000` (from middleware, not hardcoded)
- ✅ Header: `Content-Type: text/event-stream`
- ✅ No hardcoded `Access-Control-Allow-Origin: *` header
- ✅ Streaming data received

### Test 3b: Disallowed Origin (Should Fail)

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Origin: http://evil.com" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Litecoin?", "chat_history": []}' \
  -v --no-buffer
```

**Expected Result:**
- ⚠️ Status: May be `200 OK` (server processes request)
- ❌ Header: `Access-Control-Allow-Origin` should NOT be `*` or `http://evil.com`
- ❌ Browser will block the response

## Test 4: Verify Allowed Methods

### Test 4a: GET Request (Should Work)

```bash
curl -X GET http://localhost:8000/health \
  -H "Origin: http://localhost:3000" \
  -v
```

**Expected Result:**
- ✅ Status: `200 OK`
- ✅ Header: `Access-Control-Allow-Origin: http://localhost:3000`

### Test 4b: POST Request (Should Work)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}' \
  -v
```

**Expected Result:**
- ✅ Status: `200 OK` (or rate limit error)
- ✅ Header: `Access-Control-Allow-Origin: http://localhost:3000`

### Test 4c: PUT Request (Should Be Blocked)

```bash
curl -X PUT http://localhost:8000/api/v1/chat \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}' \
  -v
```

**Expected Result:**
- ❌ Status: `405 Method Not Allowed` (FastAPI will reject before CORS)
- ⚠️ Or: CORS preflight will fail if browser tries OPTIONS first

### Test 4d: DELETE Request (Should Be Blocked)

```bash
curl -X DELETE http://localhost:8000/api/v1/chat \
  -H "Origin: http://localhost:3000" \
  -v
```

**Expected Result:**
- ❌ Status: `405 Method Not Allowed`

## Test 5: Verify Allowed Headers

### Test 5a: Content-Type Header (Should Work)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}' \
  -v
```

**Expected Result:**
- ✅ Status: `200 OK`
- ✅ Request succeeds with `Content-Type` header

### Test 5b: Authorization Header (Should Work)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{"query": "test", "chat_history": []}' \
  -v
```

**Expected Result:**
- ✅ Status: `200 OK` (or authentication error if endpoint requires auth)
- ✅ Request succeeds with `Authorization` header

### Test 5c: Unauthorized Header (Should Be Blocked)

```bash
curl -X OPTIONS http://localhost:8000/api/v1/chat \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: X-Malicious-Header" \
  -v
```

**Expected Result:**
- ⚠️ Preflight may succeed, but browser will block actual request
- ❌ `Access-Control-Allow-Headers` should NOT include `X-Malicious-Header`

## Test 6: Browser-Based Integration Test

### Test 6a: Frontend from Allowed Origin

1. Open browser DevTools (F12)
2. Navigate to `http://localhost:3000`
3. Open Console tab
4. Try to send a chat message
5. Check Network tab for CORS headers

**Expected Result:**
- ✅ Request succeeds
- ✅ No CORS errors in console
- ✅ Response headers show `Access-Control-Allow-Origin: http://localhost:3000`

### Test 6b: Test from Disallowed Origin (Using Browser)

1. Create a simple HTML file:
```html
<!DOCTYPE html>
<html>
<head>
    <title>CORS Test</title>
</head>
<body>
    <button onclick="testCORS()">Test CORS</button>
    <div id="result"></div>
    <script>
        async function testCORS() {
            try {
                const response = await fetch('http://localhost:8000/api/v1/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        query: 'What is Litecoin?',
                        chat_history: []
                    })
                });
                const data = await response.json();
                document.getElementById('result').textContent = 'Success: ' + JSON.stringify(data);
            } catch (error) {
                document.getElementById('result').textContent = 'Error: ' + error.message;
            }
        }
    </script>
</body>
</html>
```

2. Open this file in browser (file:// protocol or from a different origin)
3. Click "Test CORS" button
4. Check browser console

**Expected Result:**
- ❌ CORS error in console: `Access to fetch at 'http://localhost:8000/api/v1/chat' from origin 'file://' has been blocked by CORS policy`
- ✅ This confirms CORS is working correctly

## Test 7: Verify No Hardcoded Wildcard in Streaming

### Test 7a: Check Streaming Endpoint Headers

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}' \
  -I
```

**Expected Result:**
- ✅ Header: `Access-Control-Allow-Origin: http://localhost:3000` (specific origin, not `*`)
- ✅ No hardcoded `Access-Control-Allow-Origin: *` header
- ✅ Header: `Access-Control-Allow-Methods: GET, POST, OPTIONS` (from middleware)

### Test 7b: Verify Streaming Works from Browser

1. Open `http://localhost:3000` in browser
2. Open DevTools → Network tab
3. Send a chat message (uses streaming endpoint)
4. Check the `/api/v1/chat/stream` request

**Expected Result:**
- ✅ Request succeeds
- ✅ Response headers show proper CORS headers (not wildcard)
- ✅ Streaming data received correctly

## Quick Test Script

Save this as `test-cors.sh` and run it:

```bash
#!/bin/bash

BACKEND_URL="http://localhost:8000"
ALLOWED_ORIGIN="http://localhost:3000"
DISALLOWED_ORIGIN="http://evil.com"

echo "=== Test 1: Preflight with Allowed Origin ==="
curl -X OPTIONS "$BACKEND_URL/api/v1/chat" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -s -o /dev/null -w "Status: %{http_code}\n" \
  -H "Access-Control-Allow-Origin" | grep -q "$ALLOWED_ORIGIN" && echo "✅ CORS header present" || echo "❌ CORS header missing"

echo ""
echo "=== Test 2: Preflight with Disallowed Origin ==="
curl -X OPTIONS "$BACKEND_URL/api/v1/chat" \
  -H "Origin: $DISALLOWED_ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -s -o /dev/null -w "Status: %{http_code}\n"

echo ""
echo "=== Test 3: Check Streaming Endpoint Headers ==="
curl -X POST "$BACKEND_URL/api/v1/chat/stream" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}' \
  -I 2>/dev/null | grep -i "access-control" | head -5

echo ""
echo "=== Test 4: Verify No Wildcard in Streaming ==="
STREAM_HEADERS=$(curl -X POST "$BACKEND_URL/api/v1/chat/stream" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}' \
  -I 2>/dev/null | grep -i "access-control-allow-origin")

if echo "$STREAM_HEADERS" | grep -q "\*"; then
    echo "❌ Wildcard found in streaming endpoint headers!"
else
    echo "✅ No wildcard found - CORS handled by middleware"
fi

echo ""
echo "=== Test 5: Verify Methods Restriction ==="
curl -X PUT "$BACKEND_URL/api/v1/chat" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -s -o /dev/null -w "PUT Status: %{http_code}\n"

echo ""
echo "Testing complete!"
```

Make it executable and run:
```bash
chmod +x test-cors.sh
./test-cors.sh
```

## Expected Test Results Summary

| Test | Expected Result | Status |
|------|----------------|--------|
| Preflight with allowed origin | ✅ 200 OK, CORS headers present | |
| Preflight with disallowed origin | ❌ CORS header missing/blocked | |
| POST with allowed origin | ✅ 200 OK, CORS headers present | |
| POST with disallowed origin | ❌ Browser blocks response | |
| Streaming endpoint CORS | ✅ Uses middleware, no wildcard | |
| GET method | ✅ Works | |
| POST method | ✅ Works | |
| PUT method | ❌ 405 Method Not Allowed | |
| DELETE method | ❌ 405 Method Not Allowed | |
| Content-Type header | ✅ Allowed | |
| Authorization header | ✅ Allowed | |
| Unauthorized header | ❌ Blocked | |

## Troubleshooting

### Issue: CORS errors even with allowed origin
- Check that `CORS_ORIGINS` environment variable is set correctly
- Verify backend server is reading the env var: Check logs for CORS configuration
- Restart backend server after changing environment variables

### Issue: Streaming endpoint still shows wildcard
- Verify the code changes were applied (check `backend/main.py:415-424`)
- Restart backend server
- Clear browser cache

### Issue: Methods not being blocked
- FastAPI may return 405 before CORS middleware runs (this is expected)
- Check that middleware is configured correctly in `backend/main.py`

## Next Steps

After all tests pass:
1. ✅ Mark CRIT-8 as resolved in security assessment
2. ✅ Mark HIGH-NEW-1 as resolved in security assessment
3. Test in production environment with production origins
4. Update documentation if needed

