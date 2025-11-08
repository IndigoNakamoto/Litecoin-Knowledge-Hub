# Monitoring Quick Reference

## Quick Start Commands

```bash
# Start monitoring stack
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Stop monitoring stack
docker-compose -f monitoring/docker-compose.monitoring.yml down

# View logs
docker logs litecoin-prometheus
docker logs litecoin-grafana

# Restart services
docker-compose -f monitoring/docker-compose.monitoring.yml restart
```

## Service URLs

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3002 (admin/admin)

## Key Metrics Queries

### Request Rate
```promql
rate(http_requests_total[5m])
```

### Error Rate
```promql
rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m])
```

### Average Response Time
```promql
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

### Cache Hit Rate
```promql
rate(rag_cache_hits_total[5m]) / (rate(rag_cache_hits_total[5m]) + rate(rag_cache_misses_total[5m]))
```

### LLM Cost per Hour
```promql
rate(llm_cost_usd_total[1h]) * 3600
```

### Running Total Gemini Cost
```promql
sum(llm_cost_usd_total{model=~"gemini.*"})
```

### Vector Store Document Count
```promql
vector_store_documents_total
```

## Health Check Endpoints

- `GET /health` - Comprehensive health check
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /metrics` - Prometheus metrics

## Environment Variables

```bash
# Logging
LOG_LEVEL=INFO
JSON_LOGGING=false

# LangSmith (optional)
LANGCHAIN_API_KEY=your-key-here
LANGCHAIN_PROJECT=litecoin-knowledge-hub
LANGCHAIN_ENVIRONMENT=production

# Grafana
GRAFANA_ADMIN_PASSWORD=your-password
```

## File Locations

- Prometheus config: `monitoring/prometheus.yml`
- Alert rules: `monitoring/alerts.yml`
- Docker Compose: `monitoring/docker-compose.monitoring.yml`
- Grafana dashboard: `monitoring/grafana/dashboards/litecoin-knowledge-hub.json`

## Common Issues

### Backend not accessible from Prometheus
- Use `host.docker.internal:8000` for local dev
- Use `backend:8000` for Docker Compose network

### No metrics in Grafana
- Check Prometheus targets: http://localhost:9090/targets
- Verify backend `/metrics` endpoint is accessible
- Check time range in Grafana dashboard

### Alerts not firing
- Verify alert rules in Prometheus: http://localhost:9090/alerts
- Check Alertmanager is configured (if using)

