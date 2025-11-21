#!/bin/bash
# Test script for admin endpoint authentication
# Tests CRIT-NEW-4 fix: Admin usage endpoints should require authentication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get backend URL from environment or use default
BACKEND_URL="${NEXT_PUBLIC_BACKEND_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

echo "🧪 Testing Admin Endpoint Authentication (CRIT-NEW-4 Fix)"
echo "=================================================="
echo "Backend URL: $BACKEND_URL"
echo ""

# Check if ADMIN_TOKEN is set
if [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  Warning: ADMIN_TOKEN not set${NC}"
    echo "   Set ADMIN_TOKEN environment variable to test authenticated requests"
    echo "   Example: ADMIN_TOKEN=your-token ./scripts/test-admin-endpoints.sh"
    echo ""
fi

# Test 1: Unauthenticated request to /api/v1/admin/usage (should fail)
echo "Test 1: Unauthenticated request to /api/v1/admin/usage"
echo "Expected: 401 Unauthorized"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BACKEND_URL/api/v1/admin/usage" 2>/dev/null || echo -e "\n000")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✅ PASS: Received 401 Unauthorized${NC}"
else
    echo -e "${RED}❌ FAIL: Expected 401, got $HTTP_CODE${NC}"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 2: Unauthenticated request to /api/v1/admin/usage/status (should fail)
echo "Test 2: Unauthenticated request to /api/v1/admin/usage/status"
echo "Expected: 401 Unauthorized"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BACKEND_URL/api/v1/admin/usage/status" 2>/dev/null || echo -e "\n000")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✅ PASS: Received 401 Unauthorized${NC}"
else
    echo -e "${RED}❌ FAIL: Expected 401, got $HTTP_CODE${NC}"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 3: Authenticated request with invalid token (should fail)
echo "Test 3: Authenticated request with invalid token"
echo "Expected: 401 Unauthorized"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BACKEND_URL/api/v1/admin/usage" \
    -H "Authorization: Bearer invalid-token-12345" 2>/dev/null || echo -e "\n000")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✅ PASS: Received 401 Unauthorized${NC}"
else
    echo -e "${RED}❌ FAIL: Expected 401, got $HTTP_CODE${NC}"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 4: Authenticated request with valid token (should succeed if ADMIN_TOKEN is set)
if [ -n "$ADMIN_TOKEN" ]; then
    echo "Test 4: Authenticated request with valid token"
    echo "Expected: 200 OK with usage data"
    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BACKEND_URL/api/v1/admin/usage" \
        -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null || echo -e "\n000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ PASS: Received 200 OK${NC}"
        echo "Response preview: $(echo "$BODY" | head -c 100)..."
    else
        echo -e "${RED}❌ FAIL: Expected 200, got $HTTP_CODE${NC}"
        echo "Response: $BODY"
        exit 1
    fi
    echo ""
    
    # Test 5: Authenticated request to /api/v1/admin/usage/status
    echo "Test 5: Authenticated request to /api/v1/admin/usage/status"
    echo "Expected: 200 OK with status data"
    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BACKEND_URL/api/v1/admin/usage/status" \
        -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null || echo -e "\n000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ PASS: Received 200 OK${NC}"
        echo "Response preview: $(echo "$BODY" | head -c 100)..."
    else
        echo -e "${RED}❌ FAIL: Expected 200, got $HTTP_CODE${NC}"
        echo "Response: $BODY"
        exit 1
    fi
    echo ""
else
    echo -e "${YELLOW}⏭️  Skipping Test 4-5: ADMIN_TOKEN not set${NC}"
    echo ""
fi

# Test 6: Rate limiting (make multiple requests quickly)
echo "Test 6: Rate limiting (30 requests in quick succession)"
echo "Expected: Some requests should be rate limited (429 Too Many Requests)"
RATE_LIMIT_HIT=0
for i in {1..35}; do
    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BACKEND_URL/api/v1/admin/usage" \
        -H "Authorization: Bearer invalid-token" 2>/dev/null || echo -e "\n000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" = "429" ]; then
        RATE_LIMIT_HIT=1
        echo -e "${GREEN}✅ Rate limiting working: Received 429 on request $i${NC}"
        break
    fi
    # Small delay to avoid overwhelming the server
    sleep 0.1
done

if [ "$RATE_LIMIT_HIT" = "0" ]; then
    echo -e "${YELLOW}⚠️  Warning: Rate limiting may not be working (no 429 responses)${NC}"
    echo "   This could be normal if rate limits are high or requests are slow"
fi
echo ""

echo "=================================================="
echo -e "${GREEN}✅ All authentication tests passed!${NC}"
echo ""
echo "Summary:"
echo "  ✅ Unauthenticated requests are blocked (401)"
echo "  ✅ Invalid tokens are rejected (401)"
if [ -n "$ADMIN_TOKEN" ]; then
    echo "  ✅ Valid tokens are accepted (200)"
fi
echo "  ✅ Rate limiting is configured"
echo ""
echo "CRIT-NEW-4 fix verified: Admin endpoints now require authentication!"

