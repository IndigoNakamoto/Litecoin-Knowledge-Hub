# Monitoring Infrastructure Setup Guide

This guide walks you through setting up the complete monitoring infrastructure for the Litecoin Knowledge Hub, including Prometheus, Grafana, and alerting.

## Prerequisites

- Docker and Docker Compose installed
- Backend service running and accessible
- Network connectivity between monitoring stack and backend

## Quick Start

### 1. Start Monitoring Stack

```bash
# Navigate to project root
cd /path/to/Litecoin-Knowledge-Hub

# Start Prometheus and Grafana
docker-compose -f monitoring/docker-compose.monitoring.yml up -d
```

### 2. Access Services

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3002
  - Default credentials: `admin` / `admin` (change on first login)

### 3. Verify Metrics Collection

1. Open Prometheus: http://localhost:9090
2. Go to Status → Targets
3. Verify `litecoin-backend` target is UP
4. Try a query: `rate(http_requests_total[5m])`

### 4. View Dashboard

1. Open Grafana: http://localhost:3002
2. Login with default credentials
3. Navigate to Dashboards → Litecoin Knowledge Hub - Monitoring Dashboard
4. The dashboard should automatically load with metrics

## Configuration

### Prometheus Configuration

Edit `monitoring/prometheus.yml` to customize:

- **Scrape Interval**: How often to collect metrics (default: 15s)
- **Retention**: How long to keep data (default: 30 days)
- **Targets**: Add additional services to monitor

**For Local Development** (backend not in Docker):

```yaml
scrape_configs:
  - job_name: 'litecoin-backend'
    static_configs:
      - targets: ['host.docker.internal:8000']  # Use host.docker.internal for Mac/Windows
        # OR
      - targets: ['172.17.0.1:8000']  # Use Docker bridge IP for Linux
```

**For Production**:

```yaml
scrape_configs:
  - job_name: 'litecoin-backend'
    static_configs:
      - targets: ['backend:8000']  # Service name in docker-compose network
```

### Grafana Configuration

#### Change Admin Password

**For New Installations:**

Set environment variable before starting:

```bash
export GRAFANA_ADMIN_PASSWORD=your-secure-password
docker-compose -f monitoring/docker-compose.monitoring.yml up -d
```

Or edit `docker-compose.monitoring.yml`:

```yaml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-your-password}
```

**For Existing Installations:**

⚠️ **Important:** If Grafana has already been initialized, changing `GRAFANA_ADMIN_PASSWORD` in the environment variable will **not** automatically update the existing Grafana database. The password is only set on first initialization.

To update the password for an existing Grafana instance:

```bash
# Reset password using grafana-cli
docker exec litecoin-grafana grafana-cli admin reset-admin-password <new-password>
```

Or start fresh (this will delete all Grafana data, dashboards, and configurations):

```bash
# Stop and remove volumes
docker-compose -f monitoring/docker-compose.monitoring.yml down -v

# Set new password
export GRAFANA_ADMIN_PASSWORD=your-new-password

# Start fresh
docker-compose -f monitoring/docker-compose.monitoring.yml up -d
```

#### Add Data Sources

Grafana is pre-configured with Prometheus datasource. To add more:

1. Go to Configuration → Data Sources
2. Click "Add data source"
3. Select Prometheus (or other)
4. Configure connection details

### Alerting Rules

Edit `monitoring/alerts.yml` to customize alert thresholds:

- **Error Rate**: Currently alerts at >5% (line 8)
- **Response Time**: Currently alerts at P95 >5s (line 20)
- **LLM Cost**: Currently alerts at >$10/hour (line 60)
- **Cache Hit Rate**: Currently alerts at <30% (line 38)

## LangSmith Setup (Optional but Recommended)

LangSmith provides detailed LLM tracing and cost tracking.

### 1. Sign Up

1. Visit https://smith.langchain.com
2. Sign up for a free account
3. Get your API key from Settings → API Keys

### 2. Configure Backend

Add to your `.env` file:

```bash
LANGCHAIN_API_KEY=your-api-key-here
LANGCHAIN_PROJECT=litecoin-knowledge-hub
LANGCHAIN_ENVIRONMENT=production
```

### 3. Restart Backend

```bash
# Restart backend service
docker-compose restart backend
# OR if running locally
# Restart your uvicorn process
```

### 4. View Traces

1. Visit https://smith.langchain.com
2. Navigate to your project
3. View traces, filter by operation, analyze costs

## Integration with Production Docker Compose

To integrate monitoring with your main `docker-compose.prod.yml`:

```yaml
# Add to docker-compose.prod.yml
services:
  # ... existing services ...
  
  prometheus:
    # Copy from monitoring/docker-compose.monitoring.yml
    # ...
    networks:
      - default  # Use same network as backend
  
  grafana:
    # Copy from monitoring/docker-compose.monitoring.yml
    # ...
    networks:
      - default
```

Then update `monitoring/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'litecoin-backend'
    static_configs:
      - targets: ['backend:8000']  # Service name matches docker-compose
```

## Monitoring Checklist

- [ ] Prometheus is scraping metrics successfully
- [ ] Grafana dashboard displays data
- [ ] Alerts are configured (if using Alertmanager)
- [ ] LangSmith is configured (optional)
- [ ] Health check endpoints are accessible
- [ ] Metrics endpoint is accessible at `/metrics`

## Troubleshooting

### Prometheus Can't Scrape Backend

**Problem**: Target shows as DOWN in Prometheus

**Solutions**:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check network connectivity:
   ```bash
   docker exec litecoin-prometheus wget -O- http://backend:8000/metrics
   ```
3. For local dev, use `host.docker.internal:8000` instead of `backend:8000`
4. Check Prometheus logs: `docker logs litecoin-prometheus`

### Grafana Shows "No Data"

**Problem**: Dashboard panels show "No data"

**Solutions**:
1. Verify Prometheus datasource is configured correctly
2. Check if metrics exist in Prometheus:
   - Go to Prometheus → Graph
   - Try query: `up`
3. Verify time range in Grafana (try "Last 6 hours")
4. Check Grafana logs: `docker logs litecoin-grafana`

### Metrics Not Appearing

**Problem**: Custom metrics not showing up

**Solutions**:
1. Verify backend is exposing metrics: `curl http://localhost:8000/metrics`
2. Check metric names match Prometheus query
3. Ensure monitoring middleware is enabled in `main.py`
4. Check backend logs for errors

### High Memory Usage

**Problem**: Prometheus using too much memory

**Solutions**:
1. Reduce retention period in `prometheus.yml`:
   ```yaml
   - '--storage.tsdb.retention.time=7d'  # Keep only 7 days
   ```
2. Reduce scrape interval:
   ```yaml
   scrape_interval: 30s  # Instead of 15s
   ```
3. Limit number of metrics collected

## Advanced Configuration

### Custom Dashboards

1. Create dashboard in Grafana UI
2. Export JSON
3. Save to `monitoring/grafana/dashboards/`
4. Restart Grafana to auto-load

### Alertmanager Integration

To enable alert notifications:

1. Add Alertmanager service to `docker-compose.monitoring.yml`
2. Configure notification channels (email, Slack, etc.)
3. Update `prometheus.yml` alertmanager targets
4. Alerts will be sent when conditions are met

### Persistent Storage

Data is stored in Docker volumes:
- `prometheus_data`: Prometheus time-series data
- `grafana_data`: Grafana dashboards and settings

To backup:
```bash
docker run --rm -v litecoin-knowledge-hub_prometheus_data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz /data
```

## Production Recommendations

1. **Secure Grafana**: Change default password, enable HTTPS
2. **Limit Access**: Use firewall rules to restrict Prometheus/Grafana access
3. **Set Up Alerts**: Configure Alertmanager with notification channels
4. **Monitor Costs**: Set up daily cost alerts for LLM usage
5. **Regular Backups**: Backup Prometheus and Grafana data
6. **Resource Limits**: Set memory/CPU limits for containers
7. **Log Aggregation**: Integrate with centralized logging (ELK, Loki, etc.)

## Next Steps

- Set up Alertmanager for notifications
- Create custom dashboards for specific use cases
- Configure log aggregation
- Set up automated cost reporting
- Create runbooks for common alerts

