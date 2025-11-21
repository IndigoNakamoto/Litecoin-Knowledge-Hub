# Testing LLM Request Logging

This guide explains how to test the new MongoDB LLM request logging implementation.

## Quick Start

### 1. Reset All Metrics (Fresh Start)

To clear old Prometheus data and start fresh:

```bash
./scripts/reset-all-metrics.sh
```

This will:
- Clear Prometheus TSDB data
- Clear Redis spend tracking
- Remove backend cost totals JSON file
- Restart backend to reload metrics

### 2. Rebuild and Restart Services

Since we've added new code, rebuild the backend:

```bash
# Stop current services
./scripts/down-prod.sh

# Rebuild and restart
./scripts/run-prod.sh -d
```

Wait for all services to be healthy (~30-60 seconds).

### 3. Test the Logging

Run the test script:

```bash
./scripts/test-llm-logging.sh
```

This will:
1. Make a test chat request
2. Verify logs are being written to MongoDB
3. Test the admin API endpoints

### 4. Verify in Grafana

1. Open Grafana: http://localhost:3002
2. Login (default: admin/admin)
3. Check the existing dashboard - metrics should start fresh
4. Verify Prometheus metrics are being collected

### 5. Verify MongoDB Logs

Connect to MongoDB and check logs:

```bash
docker exec -it litecoin-mongodb mongosh

# Switch to database
use litecoin_rag_db

# Check recent logs
db.llm_request_logs.find().sort({timestamp: -1}).limit(5).pretty()

# Count total logs
db.llm_request_logs.countDocuments()

# Get statistics
db.llm_request_logs.aggregate([
  {
    $group: {
      _id: null,
      total_requests: { $sum: 1 },
      total_cost: { $sum: "$cost_usd" },
      total_input_tokens: { $sum: "$input_tokens" },
      total_output_tokens: { $sum: "$output_tokens" },
      avg_duration: { $avg: "$duration_seconds" }
    }
  }
])
```

## Manual Testing

### Test Chat Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Litecoin?",
    "chat_history": []
  }'
```

### Test Stream Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does Litecoin work?",
    "chat_history": []
  }'
```

### Test Admin API (Requires ADMIN_TOKEN)

First, get your ADMIN_TOKEN from `backend/.env`:

```bash
# Get stats
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  "http://localhost:8000/api/v1/admin/llm-logs/stats?hours=24"

# Get recent logs
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  "http://localhost:8000/api/v1/admin/llm-logs/recent?limit=10"
```

## What to Verify

### ✅ MongoDB Logging

- [ ] Logs are being written to `llm_request_logs` collection
- [ ] Each log entry contains: request_id, tokens, cost, duration, status
- [ ] Cache hits are properly logged
- [ ] Errors are properly logged

### ✅ Prometheus Metrics

- [ ] `llm_requests_total` counter is incrementing
- [ ] `llm_tokens_total` counter is incrementing
- [ ] `llm_cost_usd_total` counter is incrementing
- [ ] Metrics match MongoDB log data

### ✅ Grafana Dashboard

- [ ] All panels are showing data
- [ ] Token counts match MongoDB logs
- [ ] Cost calculations are correct
- [ ] Request rates are accurate

### ✅ API Endpoints

- [ ] `/api/v1/admin/llm-logs/stats` returns aggregated data
- [ ] `/api/v1/admin/llm-logs/recent` returns recent logs
- [ ] Authentication is working (requires ADMIN_TOKEN)

## Troubleshooting

### No logs in MongoDB

1. Check backend logs: `docker logs litecoin-backend`
2. Verify MongoDB connection: `docker exec -it litecoin-mongodb mongosh --eval "db.adminCommand('ping')"`
3. Check if async logging is working (look for "Logged LLM request" in logs)

### Metrics not updating in Grafana

1. Check Prometheus targets: http://localhost:9090/targets
2. Verify backend is exposing metrics: `curl http://localhost:8000/metrics`
3. Check Prometheus is scraping: http://localhost:9090/graph?g0.expr=llm_requests_total

### Admin API returns 401

1. Verify `ADMIN_TOKEN` is set in `backend/.env`
2. Check token is correct: `grep ADMIN_TOKEN backend/.env`
3. Use Bearer token format: `Authorization: Bearer YOUR_TOKEN`

## Next Steps

Once testing is complete:

1. **Add MongoDB to Grafana**: Follow [MongoDB Grafana Setup Guide](./mongodb-grafana-setup.md)
2. **Create Custom Panels**: Add panels for MongoDB-specific metrics
3. **Set Up Alerts**: Configure alerts based on MongoDB log data
4. **Historical Analysis**: Use MongoDB data for cost recalculation and analysis

