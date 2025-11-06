# Monitoring & Observability Guide

This document describes the monitoring and observability features implemented for the Litecoin Knowledge Hub.

## Overview

The monitoring system provides comprehensive visibility into:
- **Application Performance**: Request/response times, error rates, throughput
- **RAG Pipeline Metrics**: Query duration, cache performance, retrieval metrics
- **LLM Observability**: Token usage, costs, latency, traces (via LangSmith)
- **Infrastructure Health**: Service dependencies, database connectivity, vector store status
- **Business Metrics**: Query volume, document counts, webhook processing

## Architecture

The monitoring system consists of:

1. **Prometheus Metrics**: Exposed via `/metrics` endpoint
2. **Health Checks**: `/health`, `/health/live`, `/health/ready` endpoints
3. **Structured Logging**: JSON-formatted logs for production
4. **LangSmith Integration**: Optional LLM tracing and observability

## Metrics Endpoints

### Prometheus Metrics

**Endpoint**: `GET /metrics`

Returns Prometheus-formatted metrics. Can be scraped by Prometheus or viewed directly.

**Query Parameters**:
- `format`: `prometheus` (default) or `openmetrics`

**Example**:
```bash
curl http://localhost:8000/metrics
```

### Health Checks

#### Comprehensive Health Check

**Endpoint**: `GET /health`

Returns detailed health status of all services and dependencies.

**Response Example**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "check_duration_seconds": 0.15,
  "services": {
    "vector_store": {
      "status": "healthy",
      "mongodb_available": true,
      "document_counts": {
        "total": 1234,
        "published": 1200,
        "draft": 34
      }
    },
    "llm": {
      "status": "healthy",
      "api_key_configured": true
    },
    "cache": {
      "status": "healthy",
      "cache_size": 150,
      "cache_max_size": 1000,
      "cache_utilization": 0.15
    }
  }
}
```

#### Liveness Probe

**Endpoint**: `GET /health/live`

Simple liveness check for Kubernetes/Docker health checks. Returns `200 OK` if the service is running.

#### Readiness Probe

**Endpoint**: `GET /health/ready`

Readiness check indicating if the service is ready to accept traffic. Checks critical dependencies.

## Available Metrics

### HTTP Request Metrics

- `http_requests_total`: Total HTTP requests by method, endpoint, and status code
- `http_request_duration_seconds`: Request duration histogram

### RAG Pipeline Metrics

- `rag_query_duration_seconds`: Query processing duration (by query type and cache hit status)
- `rag_cache_hits_total`: Number of cache hits
- `rag_cache_misses_total`: Number of cache misses
- `rag_retrieval_duration_seconds`: Vector store retrieval duration
- `rag_documents_retrieved_total`: Number of documents retrieved per query

### LLM Observability Metrics

- `llm_requests_total`: Total LLM API requests (by model, operation, status)
- `llm_tokens_total`: Total tokens processed (by model, token type)
- `llm_cost_usd_total`: Total cost in USD (by model, operation)
- `llm_request_duration_seconds`: LLM API request duration

### Vector Store Metrics

- `vector_store_documents_total`: Total documents in vector store (by status)
- `vector_store_size_bytes`: Size of vector store in bytes
- `vector_store_health`: Health status (1 = healthy, 0 = unhealthy)

### Webhook Processing Metrics

- `webhook_processing_total`: Total webhook processing attempts (by source, operation, status)
- `webhook_processing_duration_seconds`: Webhook processing duration

## LangSmith Integration

LangSmith provides comprehensive LLM observability including:
- Detailed traces of LLM calls
- Exact token counts (input/output)
- Cost tracking per operation
- Prompt and response inspection
- Performance analytics

### Setup

1. **Get LangSmith API Key**: Sign up at https://smith.langchain.com

2. **Configure Environment Variables**:
   ```bash
   export LANGCHAIN_API_KEY="your-api-key-here"
   export LANGCHAIN_PROJECT="litecoin-knowledge-hub"  # Optional
   export LANGCHAIN_ENVIRONMENT="production"  # Optional
   ```

3. **Automatic Integration**: Once `LANGCHAIN_API_KEY` is set, LangSmith tracing is automatically enabled for all LangChain operations.

### Viewing Traces

- Visit https://smith.langchain.com
- Navigate to your project
- View traces, filter by operation, analyze costs

## Logging Configuration

### Environment Variables

- `LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) - Default: `INFO`
- `JSON_LOGGING`: Enable JSON-formatted logs (`true`/`false`) - Default: `false`

### Log Formats

**Standard Format** (default):
```
2024-01-15 10:30:00 - backend.main - INFO - Request: POST /api/v1/chat
```

**JSON Format** (when `JSON_LOGGING=true`):
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "logger": "backend.main",
  "message": "Request: POST /api/v1/chat",
  "method": "POST",
  "path": "/api/v1/chat",
  "status_code": 200,
  "duration_seconds": 1.23
}
```

## Prometheus Setup

### Quick Start

A complete Prometheus configuration is provided in `monitoring/prometheus.yml`. To start the monitoring stack:

```bash
docker-compose -f monitoring/docker-compose.monitoring.yml up -d
```

See [Setup Guide](./setup-guide.md) for detailed instructions.

### Scraping Configuration

The default configuration in `monitoring/prometheus.yml` includes:

```yaml
scrape_configs:
  - job_name: 'litecoin-backend'
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['backend:8000']
        labels:
          service: 'backend'
          component: 'api'
```

### Example Queries

**Request Rate**:
```promql
rate(http_requests_total[5m])
```

**Error Rate**:
```promql
rate(http_requests_total{status_code=~"5.."}[5m])
```

**Average Query Duration**:
```promql
rate(rag_query_duration_seconds_sum[5m]) / rate(rag_query_duration_seconds_count[5m])
```

**Cache Hit Rate**:
```promql
rate(rag_cache_hits_total[5m]) / (rate(rag_cache_hits_total[5m]) + rate(rag_cache_misses_total[5m]))
```

**LLM Cost per Hour**:
```promql
rate(llm_cost_usd_total[1h]) * 3600
```

## Grafana Dashboards

### Pre-configured Dashboard

A complete Grafana dashboard is included at `monitoring/grafana/dashboards/litecoin-knowledge-hub.json`. It includes:

1. **Application Overview**
   - Request rate
   - Error rate
   - Response time (p50, p95, p99)

2. **RAG Pipeline Performance**
   - Query duration
   - Cache hit rate
   - Documents retrieved
   - Retrieval latency

3. **LLM Observability**
   - Token usage (input/output)
   - Cost tracking
   - Request latency

4. **Infrastructure Health**
   - Vector store document counts
   - Service health status

The dashboard is automatically loaded when Grafana starts (via provisioning).

### Accessing the Dashboard

1. Start Grafana: `docker-compose -f monitoring/docker-compose.monitoring.yml up -d`
2. Open http://localhost:3002
3. Login (default: admin/admin)
4. Navigate to Dashboards → Litecoin Knowledge Hub - Monitoring Dashboard

## Alerting

### Pre-configured Alerts

Alert rules are configured in `monitoring/alerts.yml` and include:

1. **High Error Rate** - Alerts when error rate > 5% for 5 minutes
2. **Slow Response Times** - Alerts when p95 latency > 5 seconds
3. **LLM Cost Spike** - Alerts when hourly cost > $10
4. **Service Unhealthy** - Alerts when health check fails
5. **Vector Store Issues** - Alerts when vector store health = 0
6. **Low Cache Hit Rate** - Alerts when cache hit rate < 30%
7. **Slow RAG Queries** - Alerts when p95 query duration > 10s
8. **LLM Request Failures** - Alerts when LLM error rate > 0.1 req/s
9. **Webhook Processing Failures** - Alerts when webhook error rate > 0.1 failures/s

### Viewing Alerts

1. Open Prometheus: http://localhost:9090
2. Navigate to Alerts tab
3. View active alerts and their states

### Customizing Alerts

Edit `monitoring/alerts.yml` to adjust thresholds or add new alerts. Restart Prometheus to apply changes:

```bash
docker-compose -f monitoring/docker-compose.monitoring.yml restart prometheus
```

## Docker Integration

The monitoring system is fully integrated with Docker health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## Production Recommendations

1. **Enable JSON Logging**: Set `JSON_LOGGING=true` for production
2. **Set Up Prometheus**: Deploy Prometheus to scrape metrics
3. **Configure LangSmith**: Enable LLM observability for cost tracking
4. **Set Up Alerts**: Configure alerting rules for critical metrics
5. **Monitor Costs**: Track LLM costs daily to prevent unexpected charges
6. **Review Traces**: Regularly review LangSmith traces for optimization opportunities

## Troubleshooting

### Metrics Not Appearing

- Check that `/metrics` endpoint is accessible
- Verify Prometheus can reach the endpoint
- Check application logs for errors

### LangSmith Not Working

- Verify `LANGCHAIN_API_KEY` is set correctly
- Check LangSmith dashboard for traces
- Review application logs for LangSmith errors

### Health Checks Failing

- Check individual service health in `/health` response
- Verify MongoDB connection
- Check LLM API key configuration
- Review application logs for errors

## Additional Resources

- [Setup Guide](./setup-guide.md) - Complete setup instructions
- [Quick Reference](./quick-reference.md) - Quick command and query reference
- [Prometheus Documentation](https://prometheus.io/docs/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)

