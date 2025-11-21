#!/bin/bash
# Script to test the new MongoDB LLM logging implementation

set -e

echo "🧪 Testing LLM Request Logging"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Backend is not running. Please start it first with:"
    echo "   ./scripts/run-prod.sh"
    exit 1
fi

echo "✅ Backend is running"
echo ""

# Get ADMIN_TOKEN from environment or .env file
if [ -f "backend/.env" ]; then
    ADMIN_TOKEN=$(grep "^ADMIN_TOKEN=" backend/.env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || echo "")
fi

if [ -z "$ADMIN_TOKEN" ]; then
    ADMIN_TOKEN=${ADMIN_TOKEN:-""}
fi

if [ -z "$ADMIN_TOKEN" ]; then
    echo "⚠️  ADMIN_TOKEN not found. Some tests will be skipped."
    echo "   Set ADMIN_TOKEN in backend/.env to test admin endpoints"
    echo ""
fi

# Test 1: Make a chat request
echo "1️⃣  Testing chat endpoint (this will log to MongoDB)..."
CHAT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -d '{
        "query": "What is Litecoin?",
        "chat_history": []
    }')

if echo "$CHAT_RESPONSE" | grep -q "answer"; then
    echo "   ✅ Chat request successful"
else
    echo "   ❌ Chat request failed"
    echo "   Response: $CHAT_RESPONSE"
    exit 1
fi

echo ""

# Test 2: Check MongoDB logs via admin API (if token available)
if [ -n "$ADMIN_TOKEN" ]; then
    echo "2️⃣  Checking MongoDB logs via admin API..."
    LOGS_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/admin/llm-logs/recent?limit=5" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    
    if echo "$LOGS_RESPONSE" | grep -q "logs"; then
        echo "   ✅ Successfully retrieved logs from MongoDB"
        LOG_COUNT=$(echo "$LOGS_RESPONSE" | grep -o '"count":[0-9]*' | cut -d ':' -f2)
        echo "   📊 Found $LOG_COUNT recent log entries"
    else
        echo "   ⚠️  Could not retrieve logs (may need to wait a moment for async logging)"
        echo "   Response: $LOGS_RESPONSE"
    fi
else
    echo "2️⃣  ⏭️  Skipping admin API test (ADMIN_TOKEN not set)"
fi

echo ""

# Test 3: Check stats endpoint
if [ -n "$ADMIN_TOKEN" ]; then
    echo "3️⃣  Checking aggregated statistics..."
    STATS_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/admin/llm-logs/stats?hours=24" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    
    if echo "$STATS_RESPONSE" | grep -q "totals"; then
        echo "   ✅ Successfully retrieved statistics"
        TOTAL_REQUESTS=$(echo "$STATS_RESPONSE" | grep -o '"total_requests":[0-9]*' | cut -d ':' -f2)
        echo "   📊 Total requests in last 24h: $TOTAL_REQUESTS"
    else
        echo "   ⚠️  Could not retrieve statistics"
        echo "   Response: $STATS_RESPONSE"
    fi
else
    echo "3️⃣  ⏭️  Skipping stats test (ADMIN_TOKEN not set)"
fi

echo ""
echo "✅ Testing complete!"
echo ""
echo "📊 Next steps:"
echo "   1. Check Grafana dashboard: http://localhost:3002"
echo "   2. View MongoDB logs directly: docker exec -it litecoin-mongodb mongosh"
echo "   3. Query logs: db.llm_request_logs.find().sort({timestamp: -1}).limit(10)"
echo ""

