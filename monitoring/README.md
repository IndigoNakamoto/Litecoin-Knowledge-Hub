# Monitoring Infrastructure - Complete Setup

## Overview

The monitoring infrastructure for Litecoin Knowledge Hub is now fully configured and ready to deploy. This document summarizes what has been set up and how to use it.

## What's Included

### 1. Prometheus Configuration
- **File**: `monitoring/prometheus.yml`
- **Purpose**: Scrapes metrics from backend service
- **Features**:
  - 15-second scrape interval
  - 30-day data retention
  - Alert rule loading
  - Service discovery configuration

### 2. Alert Rules
- **File**: `monitoring/alerts.yml`
- **Purpose**: Defines alert conditions and thresholds
- **Alerts Configured**:
  - High error rates
  - Slow response times
  - Service health issues
  - LLM cost spikes
  - Cache performance issues
  - Vector store problems

### 3. Grafana Dashboard
- **File**: `monitoring/grafana/dashboards/litecoin-knowledge-hub.json`
- **Purpose**: Pre-built dashboard with key metrics
- **Panels Included**:
  - Request rate and error rate
  - Response time percentiles
  - RAG pipeline performance
  - Cache hit rate
  - Vector store document counts
  - LLM cost tracking
  - Token usage

### 4. Docker Compose Stack
- **File**: `monitoring/docker-compose.monitoring.yml`
- **Purpose**: One-command deployment of monitoring stack
- **Services**:
  - Prometheus (port 9090)
  - Grafana (port 3002)

### 5. Grafana Provisioning
- **Files**: 
  - `monitoring/grafana/provisioning/datasources/prometheus.yml`
  - `monitoring/grafana/provisioning/dashboards/dashboard.yml`
- **Purpose**: Auto-configure Grafana on startup

## Quick Start

```bash
# 1. Start monitoring stack
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# 2. Verify Prometheus is scraping
# Open http://localhost:9090/targets
# Should show "litecoin-backend" as UP

# 3. Access Grafana
# Open http://localhost:3002
# Login: admin/admin
# Dashboard should auto-load
```

## File Structure

```
monitoring/
├── prometheus.yml                    # Prometheus configuration
├── alerts.yml                        # Alert rules
├── docker-compose.monitoring.yml    # Docker Compose stack
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── prometheus.yml       # Prometheus datasource config
    │   └── dashboards/
    │       └── dashboard.yml        # Dashboard provisioning config
    └── dashboards/
        └── litecoin-knowledge-hub.json  # Main dashboard

docs/monitoring/
├── monitoring-guide.md              # Comprehensive guide
├── setup-guide.md                   # Setup instructions
├── quick-reference.md               # Quick commands/queries
└── IMPLEMENTATION_SUMMARY.md         # Implementation summary
```

## Integration Points

### Backend Integration
- Metrics endpoint: `/metrics` (Prometheus format)
- Health endpoints: `/health`, `/health/live`, `/health/ready`
- Metrics middleware: Automatically tracks HTTP requests
- RAG pipeline instrumentation: Tracks query performance
- LLM observability: Optional LangSmith integration

### Network Configuration

**For Local Development**:
- Backend runs on host machine
- Use `host.docker.internal:8000` in Prometheus config

**For Docker Compose**:
- Backend runs in Docker network
- Use `backend:8000` in Prometheus config
- Ensure services are on same network

## Next Steps

1. **Start Monitoring Stack**
   ```bash
   docker-compose -f monitoring/docker-compose.monitoring.yml up -d
   ```

2. **Verify Metrics Collection**
   - Check Prometheus targets: http://localhost:9090/targets
   - Query a metric: `rate(http_requests_total[5m])`

3. **View Dashboard**
   - Open Grafana: http://localhost:3002
   - Navigate to dashboard

4. **Configure LangSmith** (Optional)
   - Add `LANGCHAIN_API_KEY` to backend `.env`
   - Restart backend
   - View traces at https://smith.langchain.com

5. **Set Up Alerts** (Optional)
   - Configure Alertmanager for notifications
   - Add notification channels (email, Slack, etc.)

## Production Deployment

### Security Considerations

1. **Change Default Passwords**
   ```bash
   export GRAFANA_ADMIN_PASSWORD=secure-password
   ```

2. **Restrict Access**
   - Use firewall rules
   - Enable authentication
   - Use HTTPS (reverse proxy)

3. **Resource Limits**
   ```yaml
   services:
     prometheus:
       deploy:
         resources:
           limits:
             memory: 2G
             cpus: '1'
   ```

4. **Backup Strategy**
   - Backup Prometheus data volume
   - Export Grafana dashboards
   - Document alert configurations

### Scaling Considerations

- **High Volume**: Increase scrape interval, reduce retention
- **Multiple Instances**: Use Prometheus federation
- **Long-term Storage**: Integrate with Thanos or Cortex
- **High Availability**: Run multiple Prometheus instances

## Troubleshooting

See [Setup Guide](./setup-guide.md#troubleshooting) for common issues and solutions.

## Support

- **Documentation**: See `docs/monitoring/` directory
- **Prometheus Docs**: https://prometheus.io/docs/
- **Grafana Docs**: https://grafana.com/docs/
- **LangSmith Docs**: https://docs.smith.langchain.com/

