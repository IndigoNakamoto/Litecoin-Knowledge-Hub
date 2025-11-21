#!/bin/bash
# Script to check if Prometheus metrics are being recorded correctly

echo "🔍 Checking Prometheus Metrics"
echo ""

# Check if Prometheus is accessible
if ! curl -s http://localhost:9090/api/v1/status/config > /dev/null 2>&1; then
    echo "❌ Prometheus is not accessible at http://localhost:9090"
    echo "   Make sure Prometheus is running"
    exit 1
fi

echo "✅ Prometheus is accessible"
echo ""

# Check LLM metrics
echo "📊 Checking LLM Metrics:"
echo ""

# Check total requests
echo "1. Total LLM Requests:"
curl -s "http://localhost:9090/api/v1/query?query=llm_requests_total" | jq -r '.data.result[] | "   \(.metric.model) - \(.metric.operation) - \(.metric.status): \(.value[1])"' 2>/dev/null || echo "   No data or jq not installed"

echo ""

# Check total tokens
echo "2. Total LLM Tokens:"
curl -s "http://localhost:9090/api/v1/query?query=llm_tokens_total" | jq -r '.data.result[] | "   \(.metric.model) - \(.metric.token_type): \(.value[1])"' 2>/dev/null || echo "   No data or jq not installed"

echo ""

# Check rate of requests (last 5 minutes)
echo "3. Request Rate (last 5 minutes):"
curl -s "http://localhost:9090/api/v1/query?query=rate(llm_requests_total{status=\"success\"}[5m])" | jq -r '.data.result[] | "   \(.metric.model): \(.value[1]) req/s"' 2>/dev/null || echo "   No data or jq not installed"

echo ""

# Check increase in tokens (last 5 minutes)
echo "4. Token Increase (last 5 minutes):"
curl -s "http://localhost:9090/api/v1/query?query=increase(llm_tokens_total[5m])" | jq -r '.data.result[] | "   \(.metric.model) - \(.metric.token_type): \(.value[1]) tokens"' 2>/dev/null || echo "   No data or jq not installed"

echo ""

# Check the tokens per response calculation
echo "5. Tokens Per Response (calculated):"
curl -s "http://localhost:9090/api/v1/query?query=sum(increase(llm_tokens_total[5m]))%20by%20(model,%20token_type)%20/%20clamp_min(sum(increase(llm_requests_total{status=\"success\"}[5m]))%20by%20(model),%201)" | jq -r '.data.result[] | "   \(.metric.model) - \(.metric.token_type): \(.value[1]) tokens/request"' 2>/dev/null || echo "   No data or jq not installed"

echo ""
echo "💡 If you see 'No data', it means:"
echo "   - No requests have been made in the last 5 minutes, OR"
echo "   - Metrics are not being recorded"
echo ""
echo "   Try making a test request:"
echo "   curl -X POST http://localhost:8000/api/v1/chat -H 'Content-Type: application/json' -d '{\"query\":\"test\",\"chat_history\":[]}'"
echo ""

