# CORS Configuration for Cloudflare Hosting

This document outlines the CORS (Cross-Origin Resource Sharing) configuration for all services when hosting through Cloudflare tunnels.

## Cloudflare Domains

The following domains are used when hosting through Cloudflare:

- **Frontend**: `https://chat.lite.space` (and `https://www.chat.lite.space`)
- **Backend API**: `https://api.lite.space`
- **Payload CMS**: `https://cms.lite.space`
- **Admin Frontend**: `https://admin.lite.space` (and `https://www.admin.lite.space`)

## Service CORS Configuration

### Backend API (`api.lite.space`)

**Location**: `backend/main.py`

**Current Configuration**:
- Default origins include:
  - `https://chat.lite.space`
  - `https://www.chat.lite.space`
  - `https://admin.lite.space`
  - `https://www.admin.lite.space`
  - `http://localhost:3000` (development)
  - `http://localhost:3003` (admin frontend local)
  - `http://127.0.0.1:3003` (admin frontend local)

**Configuration Method**:
- Can be overridden via `CORS_ORIGINS` environment variable (comma-separated)
- Can add admin frontend URL via `ADMIN_FRONTEND_URL` environment variable
- Automatically adds localhost ports in development mode

**Allowed Methods**:
- Production: `GET`, `POST`, `PUT`, `OPTIONS`
- Development: All methods (`*`)

**Allowed Headers**:
- Production: `Content-Type`, `Authorization`, `Cache-Control`, `X-Fingerprint`
- Development: All headers (`*`)

**Credentials**: Enabled (`allow_credentials=True`)

### Payload CMS (`cms.lite.space`)

**Location**: `payload_cms/src/payload.config.ts`

**Current Configuration**:
- CORS origins include:
  - `https://chat.lite.space`
  - `https://www.chat.lite.space`
  - `https://cms.lite.space`
  - `http://localhost:3000` (development only)
  - `http://localhost:3001` (development only)

**Configuration Method**:
- Uses `FRONTEND_URL` environment variable (defaults to `https://chat.lite.space` in production)
- Automatically adds localhost URLs in development mode

**Note**: Admin frontend does not make direct requests to Payload CMS, so it doesn't need to be in the CORS origins.

### Admin Frontend (`admin.lite.space`)

**Location**: `admin-frontend/src/lib/api.ts`

**Configuration**:
- Makes requests to backend API only
- Uses `NEXT_PUBLIC_BACKEND_URL` environment variable
- No CORS configuration needed (it's a client, not a server)

### Frontend (`chat.lite.space`)

**Location**: `frontend/src/app/page.tsx` and `frontend/src/components/SuggestedQuestions.tsx`

**Configuration**:
- Makes requests to:
  - Backend API (`NEXT_PUBLIC_BACKEND_URL`)
  - Payload CMS (`NEXT_PUBLIC_PAYLOAD_URL`)
- No CORS configuration needed (it's a client, not a server)

### Monitoring Services

**Prometheus** (`127.0.0.1:9090`):
- Bound to localhost only
- No CORS configuration needed (not accessible from browser)

**Grafana** (`127.0.0.1:3002`):
- Bound to localhost only
- No CORS configuration needed (not accessible from browser)

## Request Flow

### Frontend → Backend API
1. User visits `https://chat.lite.space`
2. Frontend makes requests to `https://api.lite.space/api/v1/chat/stream`
3. Backend CORS allows `https://chat.lite.space` ✅

### Frontend → Payload CMS
1. User visits `https://chat.lite.space`
2. Frontend fetches suggested questions from `https://cms.lite.space/api/suggested-questions`
3. Payload CMS CORS allows `https://chat.lite.space` ✅

### Admin Frontend → Backend API
1. User visits `https://admin.lite.space`
2. Admin frontend makes requests to `https://api.lite.space/api/v1/admin/*`
3. Backend CORS allows `https://admin.lite.space` ✅

## Environment Variables

### Backend

```bash
# Optional: Override default CORS origins
CORS_ORIGINS=https://chat.lite.space,https://www.chat.lite.space,https://admin.lite.space,https://www.admin.lite.space

# Optional: Add admin frontend URL (automatically added to CORS)
ADMIN_FRONTEND_URL=https://admin.lite.space
```

### Payload CMS

```bash
# Optional: Override frontend URL (used for CORS/CSRF)
FRONTEND_URL=https://chat.lite.space
```

### Frontend

```bash
# Required: Backend API URL
NEXT_PUBLIC_BACKEND_URL=https://api.lite.space

# Required: Payload CMS URL
NEXT_PUBLIC_PAYLOAD_URL=https://cms.lite.space
```

### Admin Frontend

```bash
# Required: Backend API URL
NEXT_PUBLIC_BACKEND_URL=https://api.lite.space
```

## Verification

### Test Backend CORS

```bash
# Test from frontend domain
curl -H "Origin: https://chat.lite.space" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://api.lite.space/api/v1/chat/stream \
     -v

# Should return:
# Access-Control-Allow-Origin: https://chat.lite.space
# Access-Control-Allow-Methods: GET, POST, PUT, OPTIONS
# Access-Control-Allow-Headers: Content-Type, Authorization, Cache-Control, X-Fingerprint
```

### Test Payload CMS CORS

```bash
# Test from frontend domain
curl -H "Origin: https://chat.lite.space" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://cms.lite.space/api/suggested-questions \
     -v

# Should return:
# Access-Control-Allow-Origin: https://chat.lite.space
```

### Test Admin Frontend → Backend

```bash
# Test from admin frontend domain
curl -H "Origin: https://admin.lite.space" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Authorization" \
     -X OPTIONS \
     https://api.lite.space/api/v1/admin/auth/verify \
     -v

# Should return:
# Access-Control-Allow-Origin: https://admin.lite.space
# Access-Control-Allow-Methods: GET, POST, PUT, OPTIONS
# Access-Control-Allow-Headers: Content-Type, Authorization, Cache-Control, X-Fingerprint
```

## Troubleshooting

### CORS Errors in Browser Console

If you see CORS errors:

1. **Check Origin Header**: Verify the `Origin` header in the browser request matches an allowed origin
2. **Check Backend Logs**: Backend logs CORS configuration on startup:
   ```
   CORS configuration: origins=[...], methods=[...], is_dev=False
   ```
3. **Verify Environment Variables**: Ensure `CORS_ORIGINS` is set correctly if overriding defaults
4. **Check Cloudflare Configuration**: Ensure Cloudflare is not modifying CORS headers

### Common Issues

1. **Missing www variant**: If using `www.chat.lite.space`, ensure both `chat.lite.space` and `www.chat.lite.space` are in CORS origins
2. **HTTP vs HTTPS**: Ensure all production origins use `https://`
3. **Trailing Slash**: CORS origins should not have trailing slashes
4. **Wildcard Not Allowed**: Cannot use `*` with `allow_credentials=True`, must specify exact origins

## Security Considerations

1. **No Wildcards**: All origins are explicitly listed (no `*` wildcards)
2. **Credentials Enabled**: `allow_credentials=True` is set for future cookie-based auth
3. **Limited Methods**: Production only allows necessary HTTP methods
4. **Limited Headers**: Production only allows necessary headers
5. **HTTPS Only**: All production origins use HTTPS

## Updates

- **2025-01-XX**: Added `https://www.chat.lite.space` to Payload CMS CORS origins for consistency with backend configuration

