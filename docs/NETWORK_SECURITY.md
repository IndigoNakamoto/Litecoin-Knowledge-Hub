# Network Security Configuration Guide

This document describes network security configurations and recommendations for the Litecoin Knowledge Hub application.

## Current Configuration

### MongoDB Connection

**Location:** `backend/dependencies.py`, `backend/rag_pipeline.py`

**Current State:**
- Connection string stored in environment variables ✅
- Connection pooling configured ✅
- No SSL/TLS requirement ⚠️
- Connection URI may contain credentials ⚠️

**Connection String Format:**
```
mongodb://[username:password@]host:port/database?options
```

### Redis Connection

**Location:** `backend/redis_client.py`

**Current State:**
- Connection URL in environment variables ✅
- No authentication configured ⚠️
- No SSL/TLS configured ⚠️

**Connection URL Format:**
```
redis://[password@]host:port/database
```

## Recommended Configurations

### MongoDB SSL/TLS

#### Enable SSL/TLS Connections

**Update Connection String:**

```bash
# In backend/.env or environment variables
MONGO_URI=mongodb://username:password@mongodb:27017/litecoin_rag_db?ssl=true&ssl_cert_reqs=CERT_REQUIRED&ssl_ca_certs=/path/to/ca.pem
```

**Options:**
- `ssl=true` - Enable SSL/TLS
- `ssl_cert_reqs=CERT_REQUIRED` - Require certificate validation
- `ssl_ca_certs=/path/to/ca.pem` - Path to CA certificate

#### Docker Configuration

**If using MongoDB Atlas or external MongoDB with SSL:**

```python
# In dependencies.py or connection configuration
mongo_client = AsyncIOMotorClient(
    MONGO_URI,
    tls=True,  # Enable TLS
    tlsCAFile='/path/to/ca.pem',  # CA certificate
    tlsAllowInvalidCertificates=False,  # Require valid certificates
    maxPoolSize=50,
    minPoolSize=5,
    maxIdleTimeMS=30000,
    serverSelectionTimeoutMS=5000,
    retryWrites=True,
    retryReads=True
)
```

### Redis Authentication

#### Enable Redis AUTH

**Update Connection URL:**

```bash
# In environment variables
REDIS_URL=redis://:password@redis:6379/0
```

**Or with username:**
```bash
REDIS_URL=redis://username:password@redis:6379/0
```

#### Docker Redis Configuration

**Update `docker-compose.prod.yml`:**

```yaml
redis:
  image: redis:7-alpine
  container_name: litecoin-redis
  command: ["redis-server", "--requirepass", "${REDIS_PASSWORD}", "--save", "60", "1", "--loglevel", "warning"]
  volumes:
    - redis_data:/data
  restart: unless-stopped
```

**Set Redis Password:**
```bash
# In .env.docker.prod
REDIS_PASSWORD=your-strong-redis-password
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

### Redis SSL/TLS

#### Enable Redis SSL/TLS

**For Redis 6+ with SSL support:**

```bash
# Connection URL with SSL
REDIS_URL=rediss://:password@redis:6380/0?ssl_cert_reqs=required&ssl_ca_certs=/path/to/ca.pem
```

**Docker Configuration:**

```yaml
redis:
  image: redis:7-alpine
  container_name: litecoin-redis
  command: 
    - redis-server
    - --requirepass ${REDIS_PASSWORD}
    - --port 6380
    - --tls-port 6380
    - --cert-file /tls/redis.crt
    - --key-file /tls/redis.key
    - --ca-cert-file /tls/ca.crt
  volumes:
    - redis_data:/data
    - ./tls:/tls
  restart: unless-stopped
```

## Network Isolation

### Docker Networks

**Production Configuration:**

```yaml
# docker-compose.prod.yml
networks:
  internal:
    driver: bridge
    internal: true  # No external access
  external:
    driver: bridge

services:
  mongodb:
    networks:
      - internal  # Only accessible within Docker network
    # ports:  # Remove port exposure
    #   - "27017:27017"

  redis:
    networks:
      - internal  # Only accessible within Docker network
    # ports:  # Remove port exposure
    #   - "6379:6379"

  backend:
    networks:
      - internal
      - external  # Can access internet for API calls
    ports:
      - "8000:8000"  # Only expose API port

  frontend:
    networks:
      - external  # Public-facing
    ports:
      - "3000:3000"
```

### Firewall Rules

**Recommended Firewall Configuration:**

```bash
# UFW (Ubuntu Firewall) example
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow specific ports for services
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend API

# Deny MongoDB and Redis from external access
sudo ufw deny 27017/tcp  # MongoDB
sudo ufw deny 6379/tcp   # Redis

# Enable firewall
sudo ufw enable
```

**Cloud Firewall Rules (AWS/GCP/Azure):**

- Only allow traffic from:
  - Load balancer IPs (for backend)
  - CDN IPs (for frontend)
  - Your office IPs (for management)
- Block direct access to MongoDB and Redis ports
- Use security groups/VPCs for network isolation

## IP Allowlisting

### Webhook IP Allowlisting

**Configure allowed IPs for webhooks:**

```bash
# In backend/.env
WEBHOOK_ALLOWED_IPS=203.0.113.1,198.51.100.42
```

**Implementation:** See `backend/utils/webhook_security.py`

### Application-Level IP Filtering

**For additional security, implement IP filtering middleware:**

```python
# backend/middleware/ip_filter.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

ALLOWED_IPS = os.getenv("ALLOWED_IPS", "").split(",") if os.getenv("ALLOWED_IPS") else []

class IPFilterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if ALLOWED_IPS:
            client_ip = request.client.host
            if client_ip not in ALLOWED_IPS:
                raise HTTPException(status_code=403, detail="IP not allowed")
        return await call_next(request)
```

## VPN/Tunnel Configuration

### Cloudflare Tunnel

**Current Configuration:** Cloudflare tunnel configured in `docker-compose.prod.yml`

**Security Benefits:**
- DDoS protection
- SSL/TLS termination
- IP hiding
- WAF protection

**Configuration:**
```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  container_name: litecoin-cloudflared
  command: tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
  env_file:
    - ./.env.docker.prod
  environment:
    - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
```

## Security Recommendations by Environment

### Development

**Minimum Security:**
- Local network only
- No external exposure
- Basic firewall rules

### Staging

**Enhanced Security:**
- MongoDB and Redis not exposed externally
- Webhook security enabled
- SSL/TLS for external connections
- Firewall rules configured

### Production

**Maximum Security:**
- All databases internal only
- SSL/TLS required for all connections
- Webhook security enabled with IP allowlisting
- Firewall rules strict
- VPN or Cloudflare tunnel
- Network segmentation
- WAF protection

## Implementation Steps

### Phase 1: Basic Hardening (Immediate)

1. **Remove MongoDB port exposure:**
   - Already completed in `docker-compose.prod.yml` ✅

2. **Configure Redis AUTH:**
   ```bash
   # Add to docker-compose.prod.yml
   REDIS_PASSWORD=${REDIS_PASSWORD}
   ```

3. **Configure firewall rules:**
   - Block MongoDB and Redis ports
   - Allow only necessary ports

### Phase 2: SSL/TLS (Short-term)

1. **MongoDB SSL/TLS:**
   - Obtain certificates
   - Update connection strings
   - Test connections

2. **Redis SSL/TLS:**
   - Configure Redis with TLS
   - Update connection URLs
   - Test connections

### Phase 3: Advanced Security (Medium-term)

1. **Network segmentation:**
   - Create separate Docker networks
   - Implement internal networks
   - Configure VPCs (cloud)

2. **IP allowlisting:**
   - Configure webhook IPs
   - Implement middleware filtering
   - Monitor access patterns

3. **VPN/Tunnel:**
   - Set up Cloudflare tunnel
   - Configure WAF rules
   - Enable DDoS protection

## Monitoring

### Network Security Monitoring

1. **Connection Monitoring:**
   - Monitor MongoDB connections
   - Track Redis connections
   - Alert on unusual patterns

2. **Access Logging:**
   - Log all connection attempts
   - Track IP addresses
   - Monitor authentication failures

3. **Firewall Logs:**
   - Review blocked connections
   - Identify attack patterns
   - Update rules as needed

## Troubleshooting

### Connection Issues

**MongoDB Connection Failures:**
1. Verify connection string format
2. Check SSL/TLS certificates
3. Verify network access
4. Check firewall rules

**Redis Connection Failures:**
1. Verify password configuration
2. Check SSL/TLS settings
3. Verify network access
4. Check firewall rules

### SSL/TLS Issues

**Certificate Errors:**
- Verify certificate paths
- Check certificate validity
- Update certificates if expired
- Verify CA certificates

## Additional Resources

- [MongoDB SSL/TLS Configuration](https://docs.mongodb.com/manual/tutorial/configure-ssl/)
- [Redis Security Guide](https://redis.io/topics/security)
- [Docker Network Security](https://docs.docker.com/network/network-tutorial-standalone/)
- [Security Hardening Guide](./SECURITY_HARDENING.md)

