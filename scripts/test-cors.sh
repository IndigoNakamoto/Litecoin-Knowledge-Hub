#!/bin/bash

# CORS Testing Script for CRIT-8 Fix
# Tests the CORS configuration changes

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ALLOWED_ORIGIN="${ALLOWED_ORIGIN:-http://localhost:3000}"
DISALLOWED_ORIGIN="http://evil.com"

echo "🔍 Testing CORS Configuration"
echo "Backend URL: $BACKEND_URL"
echo "Allowed Origin: $ALLOWED_ORIGIN"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        ((FAILED++))
    fi
}

echo "=== Test 1: Preflight OPTIONS with Allowed Origin ==="
RESPONSE=$(curl -X OPTIONS "$BACKEND_URL/api/v1/chat" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -s -w "\n%{http_code}" \
  -o /tmp/cors_test_response.txt)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
HEADERS=$(curl -X OPTIONS "$BACKEND_URL/api/v1/chat" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -s -I)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    if echo "$HEADERS" | grep -qi "access-control-allow-origin.*$ALLOWED_ORIGIN"; then
        test_result 0 "Preflight request succeeds with correct CORS header"
    else
        test_result 1 "Preflight request succeeds but CORS header missing or incorrect"
    fi
else
    test_result 1 "Preflight request failed with HTTP $HTTP_CODE"
fi

echo ""
echo "=== Test 2: Preflight OPTIONS with Disallowed Origin ==="
HEADERS_DISALLOWED=$(curl -X OPTIONS "$BACKEND_URL/api/v1/chat" \
  -H "Origin: $DISALLOWED_ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -s -I)

if echo "$HEADERS_DISALLOWED" | grep -qi "access-control-allow-origin.*$DISALLOWED_ORIGIN"; then
    test_result 1 "Disallowed origin was allowed (security issue!)"
else
    test_result 0 "Disallowed origin correctly blocked"
fi

echo ""
echo "=== Test 3: Check Streaming Endpoint CORS Headers ==="
# Use -v to get headers, then grep for CORS headers (can't use -I with POST)
STREAM_HEADERS=$(curl -X POST "$BACKEND_URL/api/v1/chat/stream" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}' \
  -s -v 2>&1 | grep -i "< access-control")

# Check for wildcard
if echo "$STREAM_HEADERS" | grep -qi "access-control-allow-origin.*\*"; then
    test_result 1 "Wildcard (*) found in streaming endpoint headers (security issue!)"
else
    if echo "$STREAM_HEADERS" | grep -qi "access-control-allow-origin.*$ALLOWED_ORIGIN"; then
        test_result 0 "Streaming endpoint uses middleware (no wildcard, correct origin)"
    elif echo "$STREAM_HEADERS" | grep -qi "access-control-allow-origin"; then
        test_result 0 "Streaming endpoint uses middleware (no wildcard)"
    else
        test_result 1 "No CORS headers found in streaming endpoint"
    fi
fi

echo ""
echo "=== Test 4: Verify Allowed Methods ==="
# Test GET (should work)
GET_CODE=$(curl -X GET "$BACKEND_URL/health" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -s -o /dev/null -w "%{http_code}")

if [ "$GET_CODE" = "200" ]; then
    test_result 0 "GET method allowed"
else
    test_result 1 "GET method failed with HTTP $GET_CODE"
fi

# Test PUT (should be blocked)
PUT_CODE=$(curl -X PUT "$BACKEND_URL/api/v1/chat" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -s -o /dev/null -w "%{http_code}")

if [ "$PUT_CODE" = "405" ]; then
    test_result 0 "PUT method correctly blocked (405)"
else
    test_result 1 "PUT method not blocked (HTTP $PUT_CODE)"
fi

echo ""
echo "=== Test 5: Verify Allowed Headers ==="
# Test with Content-Type header
POST_RESPONSE=$(curl -X POST "$BACKEND_URL/api/v1/chat" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}' \
  -s -w "\n%{http_code}" \
  -o /dev/null 2>&1)

POST_CODE=$(echo "$POST_RESPONSE" | tail -n1)
if [ "$POST_CODE" = "200" ] || [ "$POST_CODE" = "429" ]; then
    test_result 0 "Content-Type header allowed (HTTP $POST_CODE)"
else
    test_result 1 "Content-Type header blocked (HTTP $POST_CODE)"
fi

# Test with Authorization header
AUTH_RESPONSE=$(curl -X POST "$BACKEND_URL/api/v1/chat" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{"query": "test", "chat_history": []}' \
  -s -w "\n%{http_code}" \
  -o /dev/null 2>&1)

AUTH_CODE=$(echo "$AUTH_RESPONSE" | tail -n1)
if [ "$AUTH_CODE" = "200" ] || [ "$AUTH_CODE" = "429" ]; then
    test_result 0 "Authorization header allowed (HTTP $AUTH_CODE)"
else
    test_result 1 "Authorization header blocked (HTTP $AUTH_CODE)"
fi

echo ""
echo "=== Test 6: Check CORS Headers Detail ==="
echo "Allowed Origin Headers:"
curl -X OPTIONS "$BACKEND_URL/api/v1/chat" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -s -I | grep -i "access-control" | sed 's/^/  /'

echo ""
echo "=== Summary ==="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! CORS configuration is secure.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Please review the CORS configuration.${NC}"
    exit 1
fi

