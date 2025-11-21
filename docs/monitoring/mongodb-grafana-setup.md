# MongoDB Logs in Grafana - Setup Guide

This guide explains how to visualize MongoDB LLM request logs in Grafana.

## Overview

The MongoDB logging system stores complete LLM request/response data in the `llm_request_logs` collection. To visualize this data in Grafana, we use the backend API as a data source.

## Setup Steps

### 1. Install Grafana Infinity Plugin (Optional but Recommended)

The Infinity plugin allows Grafana to query JSON APIs directly. To install:

1. Access Grafana: http://localhost:3002
2. Login with admin credentials
3. Go to **Configuration** → **Plugins**
4. Search for "Infinity"
5. Click **Install** on the "Infinity" plugin by Yesoreyeram

### 2. Add MongoDB API Data Source

#### Option A: Using Infinity Plugin (Recommended)

1. Go to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Select **Infinity**
4. Configure:
   - **Name**: `MongoDB API`
   - **URL**: `http://backend:8000` (or `http://localhost:8000` if accessing from host)
   - **Auth Type**: `Bearer Token`
   - **Bearer Token**: Your `ADMIN_TOKEN` from `backend/.env`
5. Click **Save & Test**

#### Option B: Using JSON API (Built-in)

1. Go to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Select **JSON API** (if available) or use **Infinity** plugin
4. Configure similarly to Option A

### 3. Create Dashboard Panels

Once the data source is configured, you can create panels using the API endpoints:

#### Available Endpoints

- **Stats Endpoint**: `/api/v1/admin/llm-logs/stats?hours=24`
  - Returns hourly aggregates and totals
  - Use for time-series visualizations

- **Recent Logs**: `/api/v1/admin/llm-logs/recent?limit=100`
  - Returns recent individual log entries
  - Use for tables and detailed views

#### Example Panel Queries

**Total Requests Over Time:**
```
Path: /api/v1/admin/llm-logs/stats?hours=24
Parser: JSON
Columns: hourly_aggregates[*].timestamp, hourly_aggregates[*].requests
```

**Total Cost Over Time:**
```
Path: /api/v1/admin/llm-logs/stats?hours=24
Parser: JSON
Columns: hourly_aggregates[*].timestamp, hourly_aggregates[*].cost_usd
```

**Token Usage:**
```
Path: /api/v1/admin/llm-logs/stats?hours=24
Parser: JSON
Columns: hourly_aggregates[*].timestamp, hourly_aggregates[*].input_tokens, hourly_aggregates[*].output_tokens
```

## Testing

Run the test script to verify everything is working:

```bash
./scripts/test-llm-logging.sh
```

This will:
1. Make a test chat request
2. Verify logs are being written to MongoDB
3. Test the admin API endpoints

## Manual MongoDB Query

You can also query MongoDB directly:

```bash
# Connect to MongoDB
docker exec -it litecoin-mongodb mongosh

# Query recent logs
use litecoin_rag_db
db.llm_request_logs.find().sort({timestamp: -1}).limit(10).pretty()

# Get statistics
db.llm_request_logs.aggregate([
  {
    $group: {
      _id: null,
      total_requests: { $sum: 1 },
      total_cost: { $sum: "$cost_usd" },
      total_input_tokens: { $sum: "$input_tokens" },
      total_output_tokens: { $sum: "$output_tokens" }
    }
  }
])
```

## API Authentication

All admin endpoints require Bearer token authentication:

```bash
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  http://localhost:8000/api/v1/admin/llm-logs/stats?hours=24
```

Make sure `ADMIN_TOKEN` is set in `backend/.env`.

