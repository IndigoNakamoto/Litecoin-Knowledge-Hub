# LLM Spend Limit Monitoring & Discord Alerting Feature

## Overview

This feature implements bulletproof cost controls for LLM API usage by tracking daily and hourly spend limits in Redis, exposing Prometheus metrics for Grafana monitoring, and sending real-time alerts via Discord webhooks when limits are approached or exceeded.

**Status**: 🚧 **In Development**

**Priority**: High - Prevents billing runaway situations

**Last Updated**: 2025-01-XX

---

## Table of Contents

1. [Feature Summary](#feature-summary)
2. [Business Requirements](#business-requirements)
3. [Technical Requirements](#technical-requirements)
4. [Architecture](#architecture)
5. [Implementation Details](#implementation-details)
6. [Configuration](#configuration)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [API Endpoints](#api-endpoints)
9. [Testing](#testing)
10. [Deployment](#deployment)
11. [Future Enhancements](#future-enhancements)

---

## Feature Summary

### Problem Statement

LLM API costs can spiral out of control due to:
- Infinite loops or bugs causing repeated API calls
- Unexpected traffic spikes
- Malicious or accidental abuse
- Google's quota system has latency, allowing $5-20 overage before stopping

### Solution

A multi-layered cost control system that:
1. **Pre-flight checks**: Blocks requests BEFORE API calls if they would exceed limits
2. **Real-time tracking**: Uses Redis for fast, atomic cost tracking
3. **Prometheus metrics**: Exposes metrics for Grafana dashboards
4. **Discord alerts**: Sends immediate notifications at 80% and 100% thresholds
5. **Automatic enforcement**: Hard stops prevent any overage

### Key Benefits

- ✅ **Zero surprise bills** - Hard limits prevent overages
- ✅ **Instant reaction** - Stops at exactly $5.00 ± $0.001
- ✅ **Multi-instance safe** - Works across 100+ servers via shared Redis
- ✅ **Real-time visibility** - Grafana dashboards show current usage
- ✅ **Proactive alerts** - Discord notifications before limits are hit

---

## Business Requirements

### BR-1: Daily Spend Limit
- **Requirement**: Enforce a configurable daily spend limit (default: $5.00)
- **Priority**: Critical
- **Acceptance Criteria**:
  - Daily limit is configurable via environment variable
  - Counter resets at midnight UTC
  - Requests are blocked if they would exceed the limit
  - Current usage is visible in Grafana

### BR-2: Hourly Spend Limit
- **Requirement**: Enforce a configurable hourly spend limit (default: $1.00)
- **Priority**: High
- **Acceptance Criteria**:
  - Hourly limit is configurable via environment variable
  - Counter resets at the top of each hour UTC
  - Requests are blocked if they would exceed the limit
  - Current usage is visible in Grafana

### BR-3: Pre-flight Cost Estimation
- **Requirement**: Estimate cost BEFORE making API calls
- **Priority**: Critical
- **Acceptance Criteria**:
  - Uses 10% buffer for safety
  - Assumes max output tokens for worst-case estimation
  - Blocks request if estimated cost would exceed limits

### BR-4: Real-time Monitoring
- **Requirement**: Display current usage in Grafana dashboards
- **Priority**: High
- **Acceptance Criteria**:
  - Prometheus metrics exposed for daily/hourly costs
  - Prometheus metrics exposed for daily/hourly limits
  - Percentage used calculated and displayed
  - Metrics update every 30 seconds

### BR-5: Discord Alerts
- **Requirement**: Send alerts when limits are approached or exceeded
- **Priority**: High
- **Acceptance Criteria**:
  - Alert at 80% of limit (warning)
  - Alert at 100% of limit (critical)
  - Alerts include current cost, limit, and percentage
  - Alerts are not spammed (one per threshold)

---

## Technical Requirements

### TR-1: Redis Integration
- **Requirement**: Use Redis for fast, atomic cost tracking
- **Implementation**:
  - Atomic `INCRBYFLOAT` operations for thread safety
  - TTL of 48 hours for daily keys, 2 hours for hourly keys
  - Keys format: `llm:cost:daily:YYYY-MM-DD` and `llm:cost:hourly:YYYY-MM-DD-HH`

### TR-2: Prometheus Metrics
- **Requirement**: Expose metrics for Grafana
- **Metrics**:
  - `llm_daily_cost_usd` (Gauge) - Current daily cost
  - `llm_hourly_cost_usd` (Gauge) - Current hourly cost
  - `llm_daily_limit_usd` (Gauge) - Daily limit
  - `llm_hourly_limit_usd` (Gauge) - Hourly limit
  - `llm_spend_limit_rejections_total` (Counter) - Rejected requests

### TR-3: RAG Pipeline Integration
- **Requirement**: Check limits before LLM calls in `rag_pipeline.py`
- **Implementation**:
  - Pre-flight check in `aquery()` method
  - Estimate cost using `estimate_gemini_cost()`
  - Block request if limit would be exceeded
  - Record actual cost after successful call

### TR-4: Background Monitoring Task
- **Requirement**: Periodic task to sync metrics and check alerts
- **Implementation**:
  - Runs every 30 seconds
  - Syncs Redis values to Prometheus
  - Checks thresholds and sends Discord alerts
  - Prevents alert spam with state tracking

### TR-5: Discord Webhook Integration
- **Requirement**: Send formatted alerts to Discord
- **Implementation**:
  - Rich embeds with color coding (green/yellow/red)
  - Includes current cost, limit, percentage, and remaining
  - Handles webhook failures gracefully

---

## Architecture

### Component Diagram

```
┌─────────────────┐
│  RAG Pipeline   │
│  (rag_pipeline) │
└────────┬────────┘
         │
         │ 1. Pre-flight check
         ▼
┌─────────────────────────┐
│  Spend Limit Module     │
│  (spend_limit.py)       │
│  - check_spend_limit()  │
│  - record_spend()       │
└────────┬────────────────┘
         │
         ├──► Redis (Atomic counters)
         │    - llm:cost:daily:YYYY-MM-DD
         │    - llm:cost:hourly:YYYY-MM-DD-HH
         │
         ├──► Prometheus Metrics
         │    - llm_daily_cost_usd
         │    - llm_hourly_cost_usd
         │
         └──► Discord Alerts (via discord_alerts.py)
              - 80% threshold warning
              - 100% threshold critical
```

### Data Flow

1. **Request Flow**:
   ```
   User Request → RAG Pipeline → Pre-flight Check → 
   [If allowed] → LLM API Call → Record Actual Cost → Response
   [If blocked] → Error Response
   ```

2. **Monitoring Flow**:
   ```
   Background Task (30s) → Read Redis → Update Prometheus → 
   Check Thresholds → Send Discord Alert (if needed)
   ```

3. **Alert Flow**:
   ```
   Threshold Check → Discord Webhook → Discord Channel
   ```

---

## Implementation Details

### File Structure

```
backend/
├── monitoring/
│   ├── spend_limit.py          # Core spend limit logic
│   ├── discord_alerts.py       # Discord webhook integration
│   └── metrics.py              # Prometheus metrics (updated)
├── rag_pipeline.py             # RAG pipeline (updated)
└── main.py                     # Background task (updated)

monitoring/
├── alerts.yml                  # Prometheus alerts (updated)
└── grafana/
    └── dashboards/
        └── litecoin-knowledge-hub.json  # Dashboard (updated)
```

### Key Functions

#### `check_spend_limit(estimated_cost, model)`
- **Purpose**: Pre-flight check before API call
- **Returns**: `(allowed: bool, error_message: Optional[str], usage_info: dict)`
- **Logic**:
  1. Get current daily/hourly costs from Redis
  2. Add 10% buffer to estimated cost
  3. Check if would exceed limits
  4. Return result with usage info

#### `record_spend(actual_cost, input_tokens, output_tokens)`
- **Purpose**: Record actual cost after successful API call
- **Returns**: `dict` with updated usage info
- **Logic**:
  1. Atomic increment in Redis (daily and hourly)
  2. Update Prometheus gauges
  3. Return current usage

#### `send_spend_limit_alert(limit_type, current_cost, limit, percentage, is_exceeded)`
- **Purpose**: Send Discord alert
- **Returns**: `bool` (success/failure)
- **Logic**:
  1. Format rich embed with color coding
  2. Include usage details
  3. POST to Discord webhook

### Redis Key Schema

```
# Daily cost counter
llm:cost:daily:2025-01-15 → "4.5234" (float, TTL: 48h)

# Hourly cost counter
llm:cost:hourly:2025-01-15-14 → "0.8234" (float, TTL: 2h)

# Daily token counters
llm:tokens:daily:2025-01-15 → {
  "input": "123456",
  "output": "45678"
} (hash, TTL: 48h)

# Hourly token counters
llm:tokens:hourly:2025-01-15-14 → {
  "input": "12345",
  "output": "4567"
} (hash, TTL: 2h)
```

---

## Configuration

### Environment Variables

Add to `backend/.env`:

```bash
# Daily spend limit in USD (default: $5.00)
DAILY_SPEND_LIMIT_USD=5.00

# Hourly spend limit in USD (default: $1.00)
HOURLY_SPEND_LIMIT_USD=1.00

# Discord webhook URL for alerts (optional)
# Get from: Discord Server Settings → Integrations → Webhooks
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### Recommended Limits

| Environment | Daily Limit | Hourly Limit | Rationale |
|-------------|-------------|--------------|-----------|
| Development | $1.00 | $0.25 | Low traffic, testing |
| Staging | $5.00 | $1.00 | Moderate traffic, validation |
| Production | $50.00 | $10.00 | High traffic, business needs |

---

## Cost Estimates

### Per Million Questions

- **Without cache**: $800 / million questions
- **With cache**: $300 / million questions (estimated based on cache hit rate)

These estimates are based on current Gemini API pricing and average token usage per query. The actual cost will vary based on:
- Average query complexity and length
- Average response length
- Cache hit rate (for cached scenarios)
- Model pricing changes

**Note**: These estimates assume the use of `gemini-2.5-flash-lite` model. Costs may differ if other models are used.

---

## Monitoring & Alerts

### Grafana Dashboard Panels

#### Panel 1: Daily Spend Gauge
- **Type**: Gauge
- **Query**: `(llm_daily_cost_usd / llm_daily_limit_usd) * 100`
- **Thresholds**:
  - Green: 0-80%
  - Yellow: 80-100%
  - Red: 100%+

#### Panel 2: Hourly Spend Gauge
- **Type**: Gauge
- **Query**: `(llm_hourly_cost_usd / llm_hourly_limit_usd) * 100`
- **Thresholds**: Same as daily

#### Panel 3: Current Costs Stat
- **Type**: Stat
- **Queries**:
  - `llm_daily_cost_usd` (Daily Cost)
  - `llm_daily_limit_usd` (Daily Limit)
  - `llm_hourly_cost_usd` (Hourly Cost)
  - `llm_hourly_limit_usd` (Hourly Limit)

#### Panel 4: Rejections Counter
- **Type**: Stat
- **Query**: `sum(rate(llm_spend_limit_rejections_total[5m]))`

### Prometheus Alerts

Add to `monitoring/alerts.yml`:

```yaml
- name: llm_spend_limit_alerts
  interval: 30s
  rules:
    - alert: DailySpendLimitWarning
      expr: (llm_daily_cost_usd / llm_daily_limit_usd) * 100 >= 80
      for: 1m
      labels:
        severity: warning
        component: llm
      annotations:
        summary: "Daily LLM spend limit warning (80% threshold)"
        description: "Daily LLM cost is {{ $value | printf \"%.2f\" }}% of limit"

    - alert: DailySpendLimitExceeded
      expr: llm_daily_cost_usd >= llm_daily_limit_usd
      for: 1m
      labels:
        severity: critical
        component: llm
      annotations:
        summary: "Daily LLM spend limit EXCEEDED"
        description: "Daily LLM cost (${{ $value }}) has exceeded the limit"

    - alert: HourlySpendLimitWarning
      expr: (llm_hourly_cost_usd / llm_hourly_limit_usd) * 100 >= 80
      for: 1m
      labels:
        severity: warning
        component: llm
      annotations:
        summary: "Hourly LLM spend limit warning (80% threshold)"
        description: "Hourly LLM cost is {{ $value | printf \"%.2f\" }}% of limit"

    - alert: HourlySpendLimitExceeded
      expr: llm_hourly_cost_usd >= llm_hourly_limit_usd
      for: 1m
      labels:
        severity: critical
        component: llm
      annotations:
        summary: "Hourly LLM spend limit EXCEEDED"
        description: "Hourly LLM cost (${{ $value }}) has exceeded the limit"
```

### Discord Alert Format

**Warning Alert (80% threshold)**:
```
🚨 LLM Spend Limit WARNING - DAILY

The daily LLM spend limit has been approached.

Current Usage: $4.00 / $5.00 (80.0%)

Limit Type: DAILY
Current Cost: $4.00
Limit: $5.00
Percentage Used: 80.0%
Remaining: $1.00

Litecoin Knowledge Hub - Cost Monitoring
```

**Critical Alert (100% exceeded)**:
```
🚨 LLM Spend Limit EXCEEDED - DAILY

The daily LLM spend limit has been EXCEEDED.

Current Usage: $5.25 / $5.00 (105.0%)

[... same fields ...]
```

---

## API Endpoints

### GET `/api/v1/admin/usage`

**Description**: Get current daily and hourly usage statistics.

**Authentication**: None (consider adding auth in production)

**Response**:
```json
{
  "daily": {
    "cost_usd": 4.5234,
    "limit_usd": 5.00,
    "remaining_usd": 0.4766,
    "percentage_used": 90.47,
    "input_tokens": 123456,
    "output_tokens": 45678
  },
  "hourly": {
    "cost_usd": 0.8234,
    "limit_usd": 1.00,
    "remaining_usd": 0.1766,
    "percentage_used": 82.34,
    "input_tokens": 12345,
    "output_tokens": 4567
  }
}
```

---

## Testing

### Unit Tests

**File**: `backend/tests/test_spend_limit.py`

```python
# Test cases:
1. test_check_spend_limit_allows_request_below_limit
2. test_check_spend_limit_blocks_request_above_limit
3. test_check_spend_limit_blocks_request_at_limit
4. test_record_spend_increments_counters
5. test_record_spend_updates_prometheus_metrics
6. test_get_current_usage_returns_correct_values
7. test_daily_limit_resets_at_midnight_utc
8. test_hourly_limit_resets_at_top_of_hour
```

### Integration Tests

**File**: `backend/tests/test_spend_limit_integration.py`

```python
# Test cases:
1. test_rag_pipeline_blocks_request_when_limit_exceeded
2. test_rag_pipeline_allows_request_when_below_limit
3. test_background_task_syncs_metrics
4. test_discord_alert_sent_at_80_percent
5. test_discord_alert_sent_at_100_percent
6. test_discord_alert_not_spammed
```

### Manual Testing

1. **Set Low Limits**:
   ```bash
   export DAILY_SPEND_LIMIT_USD=0.01
   export HOURLY_SPEND_LIMIT_USD=0.01
   ```

2. **Make Requests**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat \
     -H "Content-Type: application/json" \
     -d '{"query": "What is Litecoin?", "chat_history": []}'
   ```

3. **Verify Blocking**:
   - First request should succeed
   - Subsequent requests should be blocked with error message

4. **Check Metrics**:
   ```bash
   curl http://localhost:8000/metrics | grep llm_daily_cost_usd
   ```

5. **Check Discord**:
   - Verify alerts appear in Discord channel
   - Verify alerts are not spammed

---

## Deployment

### Pre-Deployment Checklist

- [ ] Set appropriate limits in environment variables
- [ ] Configure Discord webhook URL
- [ ] Verify Redis is accessible
- [ ] Update Grafana dashboard with new panels
- [ ] Update Prometheus alerts configuration
- [ ] Test in staging environment
- [ ] Monitor first few hours after deployment

### Deployment Steps

1. **Update Code**:
   ```bash
   git pull origin main
   ```

2. **Update Environment Variables**:
   ```bash
   # Add to backend/.env
   DAILY_SPEND_LIMIT_USD=5.00
   HOURLY_SPEND_LIMIT_USD=1.00
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```

3. **Restart Services**:
   ```bash
   docker-compose restart litecoin-backend
   ```

4. **Verify Metrics**:
   ```bash
   curl http://localhost:8000/metrics | grep llm_daily
   ```

5. **Check Grafana**:
   - Open Grafana dashboard
   - Verify new panels appear
   - Verify metrics are updating

### Rollback Plan

If issues occur:

1. **Disable Feature** (temporary):
   ```bash
   # Set very high limits
   export DAILY_SPEND_LIMIT_USD=1000.00
   export HOURLY_SPEND_LIMIT_USD=1000.00
   ```

2. **Remove Code** (if needed):
   ```bash
   git revert <commit-hash>
   ```

---

## Future Enhancements

### Phase 2: Advanced Features

1. **Per-User Limits**
   - Track spend per user/session
   - Different limits for different user tiers
   - Admin override capability

2. **Dynamic Limit Adjustment**
   - Automatically adjust limits based on time of day
   - Lower limits during off-peak hours
   - Burst capacity for special events

3. **Cost Forecasting**
   - Predict when limits will be hit
   - Alert based on rate of spend, not just absolute values
   - "At current rate, limit will be hit in X hours"

4. **Multi-Model Support**
   - Separate limits for different models
   - Different pricing for different models
   - Model-specific alerts

5. **Admin Dashboard**
   - Web UI for viewing usage
   - Ability to adjust limits without restart
   - Historical cost analysis

6. **Slack Integration**
   - Alternative to Discord
   - Support multiple notification channels

7. **Email Alerts**
   - Backup notification method
   - Daily/weekly summary reports

### Phase 3: Advanced Analytics

1. **Cost Attribution**
   - Track costs by endpoint
   - Track costs by user
   - Track costs by query type

2. **Anomaly Detection**
   - Detect unusual spending patterns
   - Alert on potential abuse
   - Automatic rate limiting

3. **Budget Planning**
   - Monthly budget tracking
   - Projected monthly costs
   - Budget alerts

---

## Related Documentation

- [Monitoring Guide](./monitoring/monitoring-guide.md)
- [Environment Variables](./ENVIRONMENT_VARIABLES.md)
- [LLM Observability](./monitoring/IMPLEMENTATION_SUMMARY.md)
- [Rate Limiting](../backend/rate_limiter.py)

---

## Changelog

### 2025-01-XX - Initial Implementation
- Added spend limit module
- Added Discord alerting
- Added Prometheus metrics
- Added Grafana dashboard panels
- Added admin API endpoint

---

## Support

For questions or issues:
1. Check logs: `docker-compose logs litecoin-backend | grep spend_limit`
2. Check Redis: `redis-cli KEYS "llm:cost:*"`
3. Check metrics: `curl http://localhost:8000/metrics | grep llm_daily`
4. Check Discord webhook: Verify URL is correct and channel exists

---

## Appendix

### Discord Webhook Setup

1. Open Discord server
2. Go to **Server Settings** → **Integrations** → **Webhooks**
3. Click **New Webhook**
4. Name it (e.g., "Litecoin Hub Alerts")
5. Choose a channel (e.g., #alerts)
6. Copy the webhook URL
7. Add to `.env` file

### Redis Key Inspection

```bash
# Connect to Redis
redis-cli

# List all spend limit keys
KEYS "llm:cost:*"
KEYS "llm:tokens:*"

# Get current daily cost
GET "llm:cost:daily:2025-01-15"

# Get current hourly cost
GET "llm:cost:hourly:2025-01-15-14"

# Get token counts
HGETALL "llm:tokens:daily:2025-01-15"
```

### Prometheus Queries

```promql
# Current daily cost
llm_daily_cost_usd

# Current hourly cost
llm_hourly_cost_usd

# Daily percentage used
(llm_daily_cost_usd / llm_daily_limit_usd) * 100

# Hourly percentage used
(llm_hourly_cost_usd / llm_hourly_limit_usd) * 100

# Rejection rate
rate(llm_spend_limit_rejections_total[5m])
```

---

**Document Status**: Draft - Awaiting Implementation
**Next Review**: After initial implementation
**Owner**: Backend Team

