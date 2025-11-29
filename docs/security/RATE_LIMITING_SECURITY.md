# Rate Limiting Security Configuration

This document explains how to securely configure rate limiting to prevent IP spoofing attacks.

## Overview

The rate limiting system uses client IP addresses to track and limit requests. To prevent attackers from spoofing their IP address via the `X-Forwarded-For` header, the system implements strict header validation.

## Security Model

### Header Priority (Most Trusted First)

1. **`CF-Connecting-IP`** (Cloudflare) - **Always Trusted**
   - Set by Cloudflare Tunnel/Proxy
   - Cannot be spoofed by clients
   - Automatically used when present

2. **`X-Forwarded-For`** - **Conditionally Trusted**
   - Only trusted when `TRUST_X_FORWARDED_FOR=true`
   - **CRITICAL:** Only enable when behind a trusted reverse proxy that strips user-supplied headers
   - Default: **IGNORED** (prevents IP spoofing)

3. **`request.client.host`** - **Fallback**
   - Direct connection IP (when not behind proxy)
   - Always used as last resort

## Configuration

### Behind Cloudflare (Recommended)

**No configuration needed!** Cloudflare's `CF-Connecting-IP` header is automatically trusted.

```bash
# .env.docker.prod
# No TRUST_X_FORWARDED_FOR needed - Cloudflare header is automatically used
CLOUDFLARE_TUNNEL_TOKEN=your-token-here
```

The application automatically detects and uses `CF-Connecting-IP` when present, which cannot be spoofed by clients.

### Behind Nginx/Other Reverse Proxy

If you're using Nginx or another reverse proxy (not Cloudflare), you must:

1. **Configure the reverse proxy to strip user-supplied headers**
2. **Set `TRUST_X_FORWARDED_FOR=true`**

#### Nginx Configuration

```nginx
# Remove user-supplied X-Forwarded-For header
proxy_set_header X-Forwarded-For "";

# Use real-ip module to set trusted X-Forwarded-For
real_ip_header X-Forwarded-For;
real_ip_recursive on;

# Trust your internal network only
set_real_ip_from 10.0.0.0/8;
set_real_ip_from 172.16.0.0/12;
set_real_ip_from 192.168.0.0/16;

# If behind Cloudflare, trust Cloudflare IPs
# See: https://www.cloudflare.com/ips/
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
# ... (add all Cloudflare IP ranges if applicable)
```

#### Environment Variable

```bash
# .env.docker.prod
TRUST_X_FORWARDED_FOR=true
```

**⚠️ WARNING:** Only set this to `true` if your reverse proxy is properly configured to strip user-supplied headers. Otherwise, attackers can bypass rate limiting by spoofing the `X-Forwarded-For` header.

### Direct Connection (No Proxy)

**No configuration needed!** The system will use `request.client.host` directly.

```bash
# .env.local (development)
# TRUST_X_FORWARDED_FOR not set (defaults to false)
# System uses request.client.host
```

## IP Validation

All IP addresses are validated before use. Invalid IPs are rejected and the system falls back to the next source or returns "unknown".

## Testing

### Verify Cloudflare Header

```bash
# Test that CF-Connecting-IP is being used
curl -H "CF-Connecting-IP: 192.168.1.100" \
     -H "X-Forwarded-For: 10.0.0.1" \
     http://localhost:8000/api/v1/chat

# The rate limiter should use 192.168.1.100 (CF-Connecting-IP takes precedence)
```

### Verify X-Forwarded-For (When Trusted)

```bash
# With TRUST_X_FORWARDED_FOR=true
curl -H "X-Forwarded-For: 192.168.1.200" \
     http://localhost:8000/api/v1/chat

# The rate limiter should use 192.168.1.200
```

### Verify IP Spoofing Prevention (Default)

```bash
# With TRUST_X_FORWARDED_FOR=false (default)
curl -H "X-Forwarded-For: 192.168.1.200" \
     http://localhost:8000/api/v1/chat

# The rate limiter should IGNORE X-Forwarded-For and use request.client.host
```

## Security Best Practices

1. **Use Cloudflare when possible** - `CF-Connecting-IP` cannot be spoofed
2. **Never trust `X-Forwarded-For` without a reverse proxy** - Always configure your reverse proxy to strip user-supplied headers
3. **Test your configuration** - Verify that spoofed headers are rejected
4. **Monitor for anomalies** - Watch for unusual rate limit bypass patterns

## Troubleshooting

### Rate Limiting Not Working

**Symptom:** Rate limits are easily bypassed

**Possible Causes:**
1. `TRUST_X_FORWARDED_FOR=true` but reverse proxy not configured correctly
2. Direct connection without proxy (should use `request.client.host`)

**Solution:**
- Verify reverse proxy configuration strips user-supplied headers
- Check that `TRUST_X_FORWARDED_FOR` is only set when behind trusted proxy
- Test with spoofed headers to verify they're rejected

### IP Address Shows as "unknown"

**Symptom:** Rate limiter returns "unknown" as IP address

**Possible Causes:**
1. All IP sources are invalid or missing
2. Invalid IP format in headers

**Solution:**
- Check that reverse proxy is setting headers correctly
- Verify IP addresses are valid (IPv4 or IPv6)
- Check application logs for IP extraction warnings

## Related Documentation

- [Red Team Security Assessment](../security/RED_TEAM_ASSESSMENT_NOV_2025.md) - CRIT-NEW-2
- [Environment Variables](../setup/ENVIRONMENT_VARIABLES.md) - `TRUST_X_FORWARDED_FOR` variable
- [HTTPS Enforcement](../deployment/HTTPS_ENFORCEMENT.md) - Reverse proxy configuration

## References

- [Cloudflare IP Ranges](https://www.cloudflare.com/ips/)
- [Nginx Real IP Module](http://nginx.org/en/docs/http/ngx_http_realip_module.html)
- [OWASP: HTTP Headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html)

