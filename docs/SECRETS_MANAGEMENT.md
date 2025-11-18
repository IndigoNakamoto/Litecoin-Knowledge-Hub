# Secrets Management Guide

This document describes secrets management procedures and best practices for the Litecoin Knowledge Hub application.

## Secrets Overview

The application uses several secrets that must be managed securely:

### Backend Secrets (`backend/.env`)

- `GOOGLE_API_KEY` - Google AI API key for Gemini LLM
- `WEBHOOK_SECRET` - Shared secret for webhook signature verification
- `MONGO_URI` - MongoDB connection string (may contain credentials)

### Payload CMS Secrets (`payload_cms/.env`)

- `PAYLOAD_SECRET` - Payload CMS secret key for JWT signing

### Production Secrets

- `CLOUDFLARE_TUNNEL_TOKEN` - Cloudflare tunnel token (if using Cloudflare tunnel)

## Security Audit Results

### Secrets Exposure in Logs ✅

**Audit Status:** Complete

**Findings:**
- No secrets are logged in plain text
- Connection strings are not logged (only connection status)
- API keys are checked for presence but values are never logged
- Error messages are sanitized to prevent secret exposure

**Verified Locations:**
- `backend/rag_pipeline.py` - API key presence checked, value not logged
- `backend/dependencies.py` - MongoDB URI not logged, only connection status
- `backend/monitoring/health.py` - API key validation without logging value
- `backend/utils/webhook_security.py` - Secret verified but not logged

### Secrets in Environment Variables ✅

**Current Implementation:**
- All secrets stored in `.env` files (not in git) ✅
- `.env` files excluded from git via `.gitignore` ✅
- Environment variables loaded at runtime ✅

## Secrets Rotation Procedures

### Rotation Schedule

- **API Keys:** Every 90 days or after security incident
- **Webhook Secrets:** Every 90 days or after security incident
- **Database Credentials:** Every 180 days or after security incident

### Rotation Process

#### 1. Generate New Secret

```bash
# For API keys or webhook secrets
openssl rand -hex 32

# Or using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 2. Update Backend Secrets

1. **Update `backend/.env`:**
   ```bash
   # Backup current .env
   cp backend/.env backend/.env.backup
   
   # Update secret
   WEBHOOK_SECRET=new-secret-here
   ```

2. **Update Payload CMS** (if rotating webhook secret):
   - Update webhook configuration with new secret
   - Ensure Payload CMS signs webhooks with new secret

3. **Restart Services:**
   ```bash
   docker-compose -f docker-compose.prod.yml restart backend
   ```

#### 3. Verify Rotation

1. Check application logs for successful startup
2. Test webhook endpoint (if webhook secret rotated)
3. Verify API functionality (if API key rotated)
4. Monitor for authentication failures

#### 4. Clean Up

1. Keep old secrets for 7 days (for rollback if needed)
2. Delete old secrets after verification
3. Update rotation documentation

### Emergency Rotation

If a secret is compromised:

1. **Immediately rotate the secret** using the process above
2. **Revoke old secret** in source system (if possible)
3. **Review logs** for unauthorized access
4. **Audit access** to identify potential breach
5. **Document incident** and security improvements

## Secrets Management Best Practices

### 1. Storage

**Current:**
- ✅ Secrets in `.env` files (not in git)
- ✅ `.env` files excluded from version control

**Recommended Improvements:**
- Use secret management service (AWS Secrets Manager, HashiCorp Vault, etc.)
- Encrypt secrets at rest
- Use environment-specific secret stores

### 2. Access Control

**Recommendations:**
- Limit access to secrets to only necessary personnel
- Use separate secrets for development, staging, and production
- Implement secret access auditing
- Use principle of least privilege

### 3. Monitoring

**Current:**
- ✅ Secrets are not logged
- ✅ Connection attempts logged without credentials

**Recommended Improvements:**
- Monitor for secret access patterns
- Alert on unusual secret usage
- Log secret access events (without exposing values)
- Track secret rotation events

### 4. Documentation

**Current:**
- ✅ Secrets documented in `ENVIRONMENT_VARIABLES.md`
- ✅ Webhook security documented in `WEBHOOK_SECURITY.md`

**Recommendations:**
- Document secret rotation procedures
- Maintain secrets inventory
- Document access controls
- Keep incident response procedures updated

## Production Deployment

### Before Deployment

1. **Audit Secrets:**
   - Verify all required secrets are configured
   - Ensure secrets are not in version control
   - Verify secrets are strong and unique

2. **Configure Secrets:**
   - Set `WEBHOOK_SECRET` in `backend/.env`
   - Set `GOOGLE_API_KEY` in `backend/.env`
   - Set `PAYLOAD_SECRET` in `payload_cms/.env`
   - Configure production-specific secrets

3. **Verify Security:**
   - Confirm secrets are not logged
   - Verify error messages don't expose secrets
   - Test secret rotation procedures

### Secrets Verification Checklist

- [ ] All required secrets configured
- [ ] Secrets are strong (minimum 32 characters for shared secrets)
- [ ] Secrets are unique for production
- [ ] Secrets are not in version control
- [ ] `.env` files are excluded from git
- [ ] Secrets rotation procedures documented
- [ ] Backup and recovery procedures for secrets documented

## Incident Response

### If Secret is Compromised

1. **Immediately rotate** the compromised secret
2. **Revoke** old secret in source system
3. **Review logs** for unauthorized access
4. **Audit** access patterns for breach indicators
5. **Document** incident and response
6. **Improve** security controls based on findings

### Monitoring

- Monitor for authentication failures
- Alert on unusual access patterns
- Review secret access logs regularly
- Track secret rotation events

## Additional Resources

- [Environment Variables Documentation](./ENVIRONMENT_VARIABLES.md)
- [Webhook Security Configuration](./WEBHOOK_SECURITY.md)
- [Security Hardening Guide](./SECURITY_HARDENING.md)

