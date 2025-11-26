# Security Headers Testing Guide

This guide explains how to test the security headers implementation for CRIT-6.

## Quick Start

### Automated Testing (Backend)

Run the automated test script:

```bash
# From project root
cd backend/tests
python3 test_security_headers.py

# Or with custom backend URL
python3 test_security_headers.py http://localhost:8000

# Test in production mode (expects HSTS)
NODE_ENV=production python3 test_security_headers.py http://localhost:8000
```

### Manual Testing with curl

#### Test Backend Headers

```bash
# Test root endpoint
curl -I http://localhost:8000/

# Test health endpoint
curl -I http://localhost:8000/health

# Test API endpoint (POST)
curl -I -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}'

# View all headers
curl -v http://localhost:8000/ 2>&1 | grep -i "security\|frame\|content-type\|referrer\|permission"
```

#### Test Frontend Headers

```bash
# Test frontend (if running)
curl -I http://localhost:3000/

# View all security headers
curl -v http://localhost:3000/ 2>&1 | grep -i "security\|frame\|content-type\|referrer\|permission\|csp"
```

## Expected Headers

### Backend (FastAPI)

All responses should include:

- ✅ `X-Content-Type-Options: nosniff`
- ✅ `X-Frame-Options: DENY`
- ✅ `Referrer-Policy: strict-origin-when-cross-origin`
- ✅ `Permissions-Policy: geolocation=(), microphone=(), camera=()`
- ✅ `Strict-Transport-Security: max-age=31536000; includeSubDomains` (production only)

### Frontend (Next.js)

All responses should include:

- ✅ `X-Content-Type-Options: nosniff`
- ✅ `X-Frame-Options: DENY`
- ✅ `Referrer-Policy: strict-origin-when-cross-origin`
- ✅ `Permissions-Policy: geolocation=(), microphone=(), camera=()`
- ✅ `Content-Security-Policy: ...` (comprehensive CSP policy)
- ✅ `Strict-Transport-Security: max-age=31536000; includeSubDomains` (production only)

## Browser Testing

### Chrome/Edge DevTools

1. Open your application in the browser
2. Open DevTools (F12)
3. Go to **Network** tab
4. Reload the page
5. Click on any request
6. Check the **Response Headers** section
7. Look for security headers listed above

### Firefox DevTools

1. Open your application in the browser
2. Open DevTools (F12)
3. Go to **Network** tab
4. Reload the page
5. Click on any request
6. Check the **Headers** tab → **Response Headers**
7. Look for security headers listed above

### Test CSP Violations

1. Open DevTools → **Console** tab
2. Look for CSP violation warnings (they appear as console errors)
3. Example: `Content Security Policy: The page's settings blocked the loading of a resource at ...`

If you see CSP violations, you may need to adjust the CSP policy in `frontend/next.config.ts`.

## Online Security Scanners

### SecurityHeaders.com

1. Visit: https://securityheaders.com/
2. Enter your production URL
3. Review the security headers score
4. Should get an "A" or "A+" rating

### Mozilla Observatory

1. Visit: https://observatory.mozilla.org/
2. Enter your production URL
3. Run the scan
4. Review the security headers section

### SSL Labs (for HTTPS/HSTS)

1. Visit: https://www.ssllabs.com/ssltest/
2. Enter your production domain
3. Check HSTS configuration

## Testing in Different Environments

### Development Environment

```bash
# Backend should NOT have HSTS
curl -I http://localhost:8000/ | grep -i "strict-transport"

# Should return nothing (HSTS not present)
```

### Production Environment

```bash
# Backend should have HSTS
curl -I https://api.lite.space/ | grep -i "strict-transport"

# Should return: Strict-Transport-Security: max-age=31536000; includeSubDomains
```

## Testing CSP Policy

### Check CSP in Browser

1. Open DevTools → **Console**
2. Run: `document.querySelector('meta[http-equiv="Content-Security-Policy"]')`
3. Or check Response Headers for `Content-Security-Policy` header

### Test CSP Directives

The CSP should allow:
- ✅ Scripts from same origin (`'self'`)
- ✅ Styles from same origin and `fonts.googleapis.com`
- ✅ Fonts from `fonts.gstatic.com` and `data:`
- ✅ Images from same origin, `data:`, and `https:`
- ✅ API connections to backend and Payload CMS URLs

### Common CSP Issues

If you see CSP violations:

1. **Inline scripts blocked**: Next.js may need `'unsafe-inline'` (already included)
2. **External fonts blocked**: Check `font-src` directive includes `fonts.gstatic.com`
3. **API calls blocked**: Check `connect-src` includes your backend and Payload CMS URLs
4. **Images blocked**: Check `img-src` includes `https:` for external images

## Docker Testing

### Test in Docker Compose

```bash
# Start services
docker-compose -f docker-compose.prod.yml up -d

# Test backend
curl -I http://localhost:8000/

# Test frontend
curl -I http://localhost:3000/

# Run automated tests
docker-compose -f docker-compose.prod.yml exec backend python3 /app/backend/tests/test_security_headers.py http://localhost:8000
```

## Integration with CI/CD

Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Test Security Headers
  run: |
    cd backend/tests
    python3 test_security_headers.py ${{ env.BACKEND_URL }}
```

## Troubleshooting

### Headers Not Appearing

1. **Backend**: Check middleware is registered in `backend/main.py`
2. **Frontend**: Check `headers()` function in `frontend/next.config.ts`
3. **Caching**: Clear browser cache or use incognito mode
4. **Proxy/CDN**: Check if Cloudflare or other proxies are stripping headers

### HSTS in Development

If HSTS appears in development:
- Check `NODE_ENV` environment variable
- Backend checks: `NODE_ENV == "production"` or `ENVIRONMENT == "production"`
- Frontend checks: `NODE_ENV === 'production'`

### CSP Blocking Resources

1. Check browser console for CSP violation messages
2. Identify which resource is blocked
3. Update CSP in `frontend/next.config.ts` to allow the resource
4. Test again

## Verification Checklist

- [ ] All required headers present in backend responses
- [ ] All required headers present in frontend responses
- [ ] CSP policy allows all necessary resources
- [ ] HSTS only present in production
- [ ] No CSP violations in browser console
- [ ] SecurityHeaders.com gives A or A+ rating
- [ ] Headers work in both development and production
- [ ] Headers work through Cloudflare tunnel (production)

## Additional Resources

- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [MDN Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [MDN HTTP Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)

