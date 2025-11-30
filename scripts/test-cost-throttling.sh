#!/bin/bash
# Quick test script for cost throttling atomic optimization
# Usage: ./scripts/test-cost-throttling.sh

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# For testing, use a simple hash fingerprint (no challenge)
# This works if challenge-response is disabled, or we can generate a challenge first
# If challenge-response is enabled, you may need to disable it for testing:
#   - Set ENABLE_CHALLENGE_RESPONSE=false in .env.docker.dev
#   - Or disable via admin dashboard
FINGERPRINT="${FINGERPRINT:-test-hash-$(date +%s)}"

echo "🧪 Testing Cost Throttling Atomic Optimization"
echo "================================================"
echo ""
echo "Backend URL: $BACKEND_URL"
echo "Fingerprint: $FINGERPRINT"
echo ""
echo "ℹ️  Note: If you see 403 errors, challenge-response may be enabled."
echo "   Disable it for testing: ENABLE_CHALLENGE_RESPONSE=false"
echo ""

# Check if backend is running
if ! curl -s -f "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo "❌ Error: Backend is not running at $BACKEND_URL"
    echo "   Start it with: ./scripts/run-dev.sh"
    exit 1
fi

echo "✅ Backend is running"
echo ""

# Test 1: Single request (should succeed if below threshold)
echo "Test 1: Single request (should succeed)"
echo "----------------------------------------"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$BACKEND_URL/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -H "X-Fingerprint: $FINGERPRINT" \
  -d '{
    "query": "What is Litecoin?",
    "chat_history": []
  }' 2>&1)

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ Request succeeded (Status: $HTTP_STATUS)"
elif [ "$HTTP_STATUS" = "429" ]; then
    echo "⚠️  Request was throttled (Status: $HTTP_STATUS)"
    echo "   This is expected if cost limits are already exceeded"
else
    echo "❌ Unexpected status: $HTTP_STATUS"
    echo "   Response: $BODY"
fi
echo ""

# Test 2: Multiple rapid requests (should trigger throttling)
echo "Test 2: Multiple rapid requests (should trigger throttling)"
echo "------------------------------------------------------------"
echo "Sending 5 requests rapidly..."

SUCCESS_COUNT=0
THROTTLED_COUNT=0
ERROR_COUNT=0

for i in {1..5}; do
    RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$BACKEND_URL/api/v1/chat/stream" \
      -H "Content-Type: application/json" \
      -H "X-Fingerprint: $FINGERPRINT" \
      -d "{
        \"query\": \"Test request $i\",
        \"chat_history\": []
      }" 2>&1)
    
    HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
    
    if [ "$HTTP_STATUS" = "200" ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        echo "  Request $i: ✅ Succeeded"
    elif [ "$HTTP_STATUS" = "429" ]; then
        THROTTLED_COUNT=$((THROTTLED_COUNT + 1))
        echo "  Request $i: ⚠️  Throttled"
    else
        ERROR_COUNT=$((ERROR_COUNT + 1))
        echo "  Request $i: ❌ Error (Status: $HTTP_STATUS)"
    fi
    
    # Small delay to avoid overwhelming
    sleep 0.1
done

echo ""
echo "Results:"
echo "  ✅ Succeeded: $SUCCESS_COUNT"
echo "  ⚠️  Throttled: $THROTTLED_COUNT"
echo "  ❌ Errors: $ERROR_COUNT"
echo ""

# Test 3: Concurrent requests (race condition test)
echo "Test 3: Concurrent requests (race condition test)"
echo "-------------------------------------------------"
echo "Sending 5 concurrent requests..."

CONCURRENT_SUCCESS=0
CONCURRENT_THROTTLED=0
CONCURRENT_ERROR=0

for i in {1..5}; do
    (
        RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$BACKEND_URL/api/v1/chat/stream" \
          -H "Content-Type: application/json" \
          -H "X-Fingerprint: ${FINGERPRINT}-concurrent" \
          -d "{
            \"query\": \"Concurrent test $i\",
            \"chat_history\": []
          }" 2>&1)
        
        HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
        
        if [ "$HTTP_STATUS" = "200" ]; then
            echo "  Concurrent request $i: ✅ Succeeded"
            echo "SUCCESS" > /tmp/concurrent_result_$i
        elif [ "$HTTP_STATUS" = "429" ]; then
            echo "  Concurrent request $i: ⚠️  Throttled"
            echo "THROTTLED" > /tmp/concurrent_result_$i
        else
            echo "  Concurrent request $i: ❌ Error (Status: $HTTP_STATUS)"
            echo "ERROR" > /tmp/concurrent_result_$i
        fi
    ) &
done

wait

# Count results from temp files
for i in {1..5}; do
    if [ -f "/tmp/concurrent_result_$i" ]; then
        RESULT=$(cat /tmp/concurrent_result_$i)
        case "$RESULT" in
            SUCCESS) CONCURRENT_SUCCESS=$((CONCURRENT_SUCCESS + 1)) ;;
            THROTTLED) CONCURRENT_THROTTLED=$((CONCURRENT_THROTTLED + 1)) ;;
            ERROR) CONCURRENT_ERROR=$((CONCURRENT_ERROR + 1)) ;;
        esac
        rm -f "/tmp/concurrent_result_$i"
    fi
done

echo ""
echo "Concurrent Results:"
echo "  ✅ Succeeded: $CONCURRENT_SUCCESS"
echo "  ⚠️  Throttled: $CONCURRENT_THROTTLED"
echo "  ❌ Errors: $CONCURRENT_ERROR"
echo ""
echo "💡 If atomic optimization works correctly:"
echo "   - Only requests within cost limits should succeed"
echo "   - No race conditions (all requests see consistent state)"
echo ""

# Summary
echo "================================================"
echo "Test Summary"
echo "================================================"
echo ""
echo "To verify the optimization is working:"
echo "1. Check backend logs for Lua script execution:"
echo "   docker logs litecoin-backend | grep -i 'cost\|throttle'"
echo ""
echo "2. Check Redis keys:"
echo "   docker exec -it litecoin-redis redis-cli"
echo "   KEYS llm:cost:*"
echo "   KEYS llm:throttle:*"
echo ""
echo "3. Enable cost throttling in dev mode if needed:"
echo "   - Set ENABLE_COST_THROTTLING=true in .env.docker.dev"
echo "   - Or enable via admin dashboard"
echo ""
echo "4. If you see 403 errors (invalid challenge):"
echo "   - Set ENABLE_CHALLENGE_RESPONSE=false in .env.docker.dev"
echo "   - Or disable via admin dashboard"
echo "   - Or use a valid challenge in the fingerprint"
echo ""
echo "For detailed testing guide, see:"
echo "   docs/testing/TESTING_COST_THROTTLING_ATOMIC.md"
echo ""

