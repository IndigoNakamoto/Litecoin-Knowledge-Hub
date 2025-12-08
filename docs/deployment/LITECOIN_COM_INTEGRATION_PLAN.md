# Litecoin.com Integration Plan

This document outlines the plan to integrate the Litecoin Knowledge Hub chat interface into litecoin.com/chat while keeping backend services at lite.space.

## Overview

### Target Architecture

| Service | Domain | Notes |
|---------|--------|-------|
| **Frontend (Chat UI)** | `litecoin.com/chat` | User-facing chat interface |
| **Backend API** | `api.lite.space` | Keep existing - no change |
| **Payload CMS** | `cms.lite.space` | Keep existing - no change |
| **Admin Frontend** | `admin.lite.space` | Keep existing - no change |
| **Grafana** | `grafana.lite.space` (new) | Expose monitoring dashboard |

### Why Reverse Proxy (Not Codebase Merge)?

- **User Trust**: Everything happens on `litecoin.com`
- **Developer Speed**: Completely isolated backend/frontend maintenance
- **No Dependency Conflicts**: Avoids nightmare of merging codebases
- **Independent Deployments**: Can update backend without touching litecoin.com config
- **Simple Rollback**: Just disable the Worker route

---

## Current Setup

### Services (Docker Compose)

```
litecoin-frontend       → port 3000 → chat.lite.space
litecoin-backend        → port 8000 → api.lite.space
litecoin-payload-cms    → port 3001 → cms.lite.space
litecoin-admin-frontend → port 3003 → admin.lite.space
litecoin-grafana        → port 3002 → localhost only (to be exposed)
litecoin-prometheus     → port 9090 → localhost only
```

### Cloudflare Tunnel

Currently using `cloudflared` container with tunnel token to expose:
- `chat.lite.space` → frontend
- `api.lite.space` → backend
- `cms.lite.space` → payload_cms
- `admin.lite.space` → admin_frontend

### Integration Architecture

**New**: Guest tunnel from litecoin.com to your frontend:
- `chat.litecoin.com` → Guest tunnel → `frontend:3000` (internal, users never see this)
- Worker routes `litecoin.com/chat*` → `chat.litecoin.com/chat*` (transparent proxy)

---

## ⚠️ Critical: The Asset Loading Problem

### Why Path Stripping Breaks Everything

A naive approach would strip `/chat` from the path when proxying:

```javascript
// ❌ WRONG - DO NOT DO THIS
url.pathname.replace('/chat', '')
```

**Here's what breaks:**

1. User visits `litecoin.com/chat`
2. Worker requests `chat.lite.space/` (root)
3. Next.js returns HTML saying: *"Load styles from `/_next/static/style.css`"*
4. Browser (on `litecoin.com/chat`) sees relative link, tries to fetch `litecoin.com/_next/static/style.css`
5. **FAILURE**: That request doesn't start with `/chat`, so Worker ignores it
6. Request hits Webflow, which 404s
7. **Site is broken** - no CSS, no JS, nothing works

### The Solution: Keep the Path + Use basePath

The upstream Next.js app must **expect** the `/chat` prefix. This is mandatory.

---

## Integration Tasks (Optimized Order)

### Phase 1: Frontend Configuration (Do This First)

#### 1.1 Next.js basePath Configuration (MANDATORY)

**File: `frontend/next.config.ts`**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,
  
  // MANDATORY: Forces Next.js to generate links like /chat/_next/static/...
  basePath: '/chat',
  
  async rewrites() {
    const backendUrl = (process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || 'http://localhost:8000');
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ]
  },
  // ... rest of existing config
}
```

> **Note**: After deploying this change, `chat.lite.space` will redirect to `chat.lite.space/chat`. This is expected and temporary until the Worker is deployed.

#### 1.2 Environment Variables

**File: `.env.docker.prod`**

```bash
# CORS must include litecoin.com
CORS_ORIGINS=https://litecoin.com,https://www.litecoin.com,https://chat.lite.space

# Backend stays at lite.space
NEXT_PUBLIC_BACKEND_URL=https://api.lite.space
NEXT_PUBLIC_PAYLOAD_URL=https://cms.lite.space
```

#### 1.3 Build and Deploy

```bash
# Rebuild frontend with basePath
docker-compose -f docker-compose.prod.yml build frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

**Verification**: Visit `chat.lite.space` - it should redirect to `chat.lite.space/chat`

---

### Phase 2: Backend CORS Update

#### 2.1 Update CORS Origins

The backend needs to accept requests from litecoin.com. No code change needed - just update the environment variable.

**File: `.env.docker.prod`**

```bash
CORS_ORIGINS=https://litecoin.com,https://www.litecoin.com,https://chat.lite.space,https://www.chat.lite.space
```

#### 2.2 Update Payload CMS CORS

**File: `payload_cms/src/payload.config.ts`**

```typescript
const corsOrigins = [
  frontendUrl,
  'https://cms.lite.space',
  'https://chat.lite.space',
  'https://litecoin.com',      // NEW
  'https://www.litecoin.com',  // NEW
]

const csrfOrigins = [
  frontendUrl,
  'https://cms.lite.space',
  'https://chat.lite.space',
  'https://litecoin.com',      // NEW
  'https://www.litecoin.com',  // NEW
]
```

#### 2.3 Deploy Backend Changes

```bash
docker-compose -f docker-compose.prod.yml up -d backend payload_cms
```

---

### Phase 3: Guest Tunnel Setup (Site Manager)

**Owner**: Site Manager

Since the site manager can only proxy to `*.litecoin.com` subdomains (not external domains like `chat.lite.space`), we use a **guest tunnel** approach.

#### 3.1 Create Guest Tunnel (Site Manager)

The site manager needs to:

1. **Create a new tunnel** in Cloudflare Zero Trust Dashboard:
   - Go to Zero Trust → Networks → Tunnels
   - Click "Create a tunnel"
   - Name: `chat-frontend` (or similar)

2. **Add Public Hostname**:
   - Subdomain: `chat`
   - Domain: `litecoin.com`
   - Service: `http://frontend:3000` (or your Docker service name)
   - **Important**: This creates `chat.litecoin.com` - a "backstage hallway" that users never see

3. **Get Tunnel Token**:
   - Copy the tunnel token (starts with `ey...`)
   - Send it to you

#### 3.2 Add Guest Tunnel to Docker Compose (Your Side)

Once you receive the tunnel token, add it to your setup:

**File: `.env.docker.prod`**

```bash
# Guest tunnel token from site manager (for chat.litecoin.com)
CLOUDFLARE_CHAT_TUNNEL_TOKEN=ey...  # Token from site manager
```

**File: `docker-compose.prod.yml`**

Add new service:

```yaml
  chat_tunnel:
    image: cloudflare/cloudflared:latest
    container_name: litecoin-chat-tunnel
    command: tunnel --no-autoupdate run --token ${CLOUDFLARE_CHAT_TUNNEL_TOKEN}
    env_file:
      - ./.env.docker.prod
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_CHAT_TUNNEL_TOKEN}
    depends_on:
      frontend:
        condition: service_healthy
    restart: unless-stopped
```

**Deploy the tunnel:**

```bash
docker-compose -f docker-compose.prod.yml up -d chat_tunnel
```

**Verification**: The tunnel should connect and `chat.litecoin.com` should resolve (though it won't work until Worker is set up).

---

### Phase 4: Cloudflare Worker (Site Manager)

**Owner**: Site Manager (Losh)

Once the guest tunnel is live, the site manager adds a Worker route.

#### 4.1 The Worker Code

Since Next.js is configured with `basePath: '/chat'`, the Worker should **keep the path intact** and proxy to the guest tunnel endpoint:

```javascript
// Cloudflare Worker for litecoin.com
// Route: litecoin.com/chat* → chat.litecoin.com/chat*
// (chat.litecoin.com is the guest tunnel endpoint - users never see this)

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    
    // Only intercept requests starting with /chat
    if (url.pathname.startsWith('/chat')) {
      // Create target URL - keep the FULL path (including /chat)
      // Proxy to the "backstage hallway" (guest tunnel endpoint)
      const targetUrl = new URL(request.url);
      targetUrl.hostname = 'chat.litecoin.com';  // Guest tunnel endpoint
      
      // Forward the request as-is
      const newRequest = new Request(targetUrl, {
        method: request.method,
        headers: request.headers,
        body: request.body,
        redirect: 'manual',
      });
      
      return fetch(newRequest);
    }
    
    // Pass everything else to the main site (Webflow/Next.js)
    return fetch(request);
  }
}
```

#### 4.2 Worker Route Configuration

In Cloudflare Dashboard → Workers & Pages → Your Worker:

- **Route**: `litecoin.com/chat*` (note the wildcard `*`)
- **Zone**: litecoin.com

**Critical**: The wildcard `*` must be present to catch sub-resources like `/chat/_next/static/...`

#### 4.3 What the Worker Does

| Request | Worker Action | Result |
|---------|--------------|--------|
| `litecoin.com/chat` | → `chat.litecoin.com/chat` → Guest tunnel → `frontend:3000` | Main page loads |
| `litecoin.com/chat/_next/static/abc.js` | → `chat.litecoin.com/chat/_next/static/abc.js` → Tunnel | Assets load correctly |
| `litecoin.com/chat/api/v1/chat` | → `chat.litecoin.com/chat/api/v1/chat` → Tunnel | API calls work |
| `litecoin.com/wallet` | Pass through | Handled by existing site |

#### 4.4 Why This Approach?

- **Constraint**: Site manager can only proxy to `*.litecoin.com` (not `chat.lite.space`)
- **Solution**: Guest tunnel creates `chat.litecoin.com` as an internal endpoint
- **User Experience**: Users see `litecoin.com/chat` in address bar (transparent proxy)
- **No Port Exposure**: Tunnel handles connectivity, no need to expose ports

---

### Phase 5: Turnstile Integration

Cloudflare Turnstile provides bot protection. The backend already supports it.

#### 4.1 Create Turnstile Widget (Cloudflare Dashboard)

1. Go to Cloudflare Dashboard → Turnstile
2. Create a new widget:
   - **Name**: Litecoin Knowledge Hub
   - **Domains**: `litecoin.com`, `chat.lite.space`, `localhost` (for dev)
   - **Widget Mode**: Managed (recommended) or Invisible
3. Copy:
   - **Site Key** (public, for frontend)
   - **Secret Key** (private, for backend)

#### 4.2 Backend Configuration (Already Implemented)

**File: `backend/.env`**

```bash
ENABLE_TURNSTILE=true
TURNSTILE_SECRET_KEY=0x4AAAAAAA...your-secret-key
```

The backend already has the verification logic in `backend/utils/turnstile.py` and integration in `backend/main.py`.

#### 4.3 Frontend Integration (New Implementation Needed)

**Step 1: Add Turnstile Script**

**File: `frontend/src/app/layout.tsx`**

```tsx
import Script from 'next/script'

export default function RootLayout({ children }) {
  return (
    <html>
      <head>
        {/* Turnstile Script */}
        <Script 
          src="https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad" 
          async 
          defer 
        />
      </head>
      <body>{children}</body>
    </html>
  )
}
```

**Step 2: Create Turnstile Component**

**File: `frontend/src/components/TurnstileWidget.tsx`**

```tsx
'use client'
import { useEffect, useRef, useCallback } from 'react'

declare global {
  interface Window {
    turnstile: {
      render: (element: HTMLElement, options: any) => string
      reset: (widgetId: string) => void
      remove: (widgetId: string) => void
    }
    onTurnstileLoad?: () => void
  }
}

interface TurnstileWidgetProps {
  onVerify: (token: string) => void
  onError?: () => void
  onExpire?: () => void
  invisible?: boolean
}

export function TurnstileWidget({ 
  onVerify, 
  onError, 
  onExpire,
  invisible = false 
}: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const widgetIdRef = useRef<string>()

  const renderWidget = useCallback(() => {
    const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY
    if (!siteKey || !containerRef.current || widgetIdRef.current) return

    widgetIdRef.current = window.turnstile.render(containerRef.current, {
      sitekey: siteKey,
      callback: onVerify,
      'error-callback': onError,
      'expired-callback': onExpire,
      theme: 'auto',
      size: invisible ? 'invisible' : 'normal',
    })
  }, [onVerify, onError, onExpire, invisible])

  useEffect(() => {
    if (window.turnstile) {
      renderWidget()
    } else {
      window.onTurnstileLoad = renderWidget
    }

    return () => {
      if (widgetIdRef.current) {
        window.turnstile?.remove(widgetIdRef.current)
      }
    }
  }, [renderWidget])

  return <div ref={containerRef} className={invisible ? 'sr-only' : ''} />
}
```

**Step 3: Integrate with Chat**

**File: `frontend/src/components/ChatWindow.tsx`** (or equivalent)

```tsx
import { useState } from 'react'
import { TurnstileWidget } from './TurnstileWidget'

export function ChatWindow() {
  const [turnstileToken, setTurnstileToken] = useState<string>()
  const [isVerified, setIsVerified] = useState(false)

  const handleTurnstileVerify = (token: string) => {
    setTurnstileToken(token)
    setIsVerified(true)
  }

  const sendMessage = async (message: string) => {
    const response = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        turnstile_token: turnstileToken,  // Include token
      }),
    })
    // ... handle response
  }

  return (
    <div>
      {/* Show Turnstile widget if not verified */}
      {!isVerified && (
        <TurnstileWidget 
          onVerify={handleTurnstileVerify}
          onError={() => console.error('Turnstile error')}
        />
      )}
      
      {/* Chat interface */}
      {/* ... */}
    </div>
  )
}
```

**Step 4: Environment Variable**

**File: `frontend/.env.local`** (development)
```bash
NEXT_PUBLIC_TURNSTILE_SITE_KEY=1x00000000000000000000AA  # Test key
```

**Docker build arg** (production):
```yaml
frontend:
  build:
    args:
      - NEXT_PUBLIC_TURNSTILE_SITE_KEY=${TURNSTILE_SITE_KEY}
```

---

### Phase 6: Expose Grafana (Optional)

#### 5.1 Update Docker Compose

**File: `docker-compose.prod.yml`**

Change Grafana from localhost-only to tunnel-accessible:

```yaml
grafana:
  image: grafana/grafana:latest
  container_name: litecoin-grafana
  ports:
    - "3002:3000"  # Remove 127.0.0.1 to allow tunnel access
  # ... rest of config
```

#### 5.2 Add Tunnel Hostname

In Cloudflare Zero Trust Dashboard → Tunnels → Your Tunnel → Public Hostnames:

| Subdomain | Domain | Path | Service |
|-----------|--------|------|---------|
| grafana | lite.space | | http://litecoin-grafana:3000 |

#### 5.3 Protect with Cloudflare Access (Recommended)

1. Go to Cloudflare Zero Trust → Access → Applications
2. Create new application:
   - **Name**: Grafana
   - **Domain**: `grafana.lite.space`
3. Add access policy:
   - **Policy name**: Team Access
   - **Action**: Allow
   - **Include**: Emails ending in `@yourdomain.com` or specific emails

---

## Deployment Checklist (Fastest Path)

### Step 1: Update Backend CORS ✅
- [ ] Add `https://litecoin.com` to `CORS_ORIGINS` in `.env.docker.prod`
- [ ] Update Payload CMS CORS in `payload.config.ts`
- [ ] Deploy: `docker-compose -f docker-compose.prod.yml up -d backend payload_cms`

### Step 2: Update Frontend Config ✅
- [ ] Set `basePath: '/chat'` in `frontend/next.config.ts`
- [ ] Build and push to `chat.lite.space`
- [ ] **Verify**: `chat.lite.space` redirects to `chat.lite.space/chat`

### Step 3: Guest Tunnel Setup ✅
- [ ] Site manager creates tunnel: `chat.litecoin.com` → `http://frontend:3000`
- [ ] Receive tunnel token from site manager
- [ ] Add token to `.env.docker.prod` as `CLOUDFLARE_CHAT_TUNNEL_TOKEN`
- [ ] Add `chat_tunnel` service to `docker-compose.prod.yml`
- [ ] Deploy: `docker-compose -f docker-compose.prod.yml up -d chat_tunnel`
- [ ] **Verify**: Tunnel connects (check logs)

### Step 4: Site Manager Deploys Worker ✅
- [ ] Site manager adds Worker route: `litecoin.com/chat*` → `chat.litecoin.com/chat*`
- [ ] **Critical**: Wildcard `*` must match sub-resources
- [ ] **Critical**: Worker proxies to `chat.litecoin.com` (not `chat.lite.space`)
- [ ] Test from `litecoin.com/chat`

### Step 5: Turnstile (Can Be Done Later)
- [ ] Create Turnstile widget in Cloudflare Dashboard (include both domains)
- [ ] Add frontend component
- [ ] Enable on backend: `ENABLE_TURNSTILE=true`

---

## Testing

### Test CORS from litecoin.com

```bash
curl -H "Origin: https://litecoin.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://api.lite.space/api/v1/chat/stream \
     -v

# Expected response headers:
# Access-Control-Allow-Origin: https://litecoin.com
# Access-Control-Allow-Methods: GET, POST, PUT, OPTIONS
```

### Test Asset Loading

After Worker is deployed, verify in browser DevTools:
1. Open `litecoin.com/chat`
2. Network tab → check that `_next/static/*` requests return 200
3. Console → no CORS errors

---

## Rollback Plan

| Issue | Rollback Action |
|-------|-----------------|
| Worker breaks other routes | Site manager disables `/chat*` route |
| CORS errors | Revert `CORS_ORIGINS` to previous value |
| Turnstile blocking users | Set `ENABLE_TURNSTILE=false` (graceful degradation) |
| Frontend broken | Traffic can still go to `chat.lite.space/chat` directly |
| Tunnel connection issues | Check `chat_tunnel` container logs, verify token |
| Worker not routing | Site manager disables/enables route, check Worker logs |

---

## Site Manager Requirements

### What the Site Manager Needs to Do

1. **Create Guest Tunnel**:
   - Create new tunnel in Cloudflare Zero Trust Dashboard
   - Name: `chat-frontend` (or similar)
   - Add public hostname: `chat.litecoin.com` → `http://frontend:3000`
   - Copy tunnel token (starts with `ey...`) and send it to you

2. **Add Worker Route** (after tunnel is live):
   - Route: `litecoin.com/chat*` → proxy to `chat.litecoin.com/chat*`
   - Use the Worker code provided in Phase 4
   - Ensure wildcard `*` is included to catch sub-resources

### Questions for Site Manager

1. **Timeline**: When can you create the guest tunnel and send the token?
2. **Service Name**: What should the tunnel point to? (`frontend:3000`, `litecoin-frontend:3000`, etc.?)
3. **Existing Workers**: Are there existing Workers we need to integrate with?
4. **Headers**: Any specific headers that need to be preserved or added?
5. **Caching**: Any Cloudflare cache rules that might affect `/chat`?
6. **Turnstile**: Do you have an existing Turnstile widget, or should we create one?

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Backend CORS update | 1 hour | None |
| Frontend basePath config | 2-4 hours | None |
| Guest tunnel setup | 1 hour | Site manager creates tunnel, sends token |
| Add tunnel to docker-compose | 30 min | After receiving token |
| Worker deployment | 1-2 hours | Site manager availability, after tunnel is live |
| Testing | 2-4 hours | All above complete |
| Turnstile integration | 1 day | Can be done after launch |
| **Total** | **1-2 days** | Depends on site manager timeline |

---

## Summary

### Request Flow

```
User Browser
    │
    ▼
litecoin.com/chat  (User sees this in address bar)
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│                    litecoin.com (Cloudflare)                  │
│                                                               │
│   /wallet, /blog, etc.        /chat/*                        │
│         │                         │                           │
│         ▼                         ▼                           │
│   ┌──────────┐            ┌──────────────┐                   │
│   │ Webflow/ │            │  Cloudflare  │                   │
│   │ Next.js  │            │   Worker     │                   │
│   └──────────┘            └──────┬───────┘                   │
│                                  │                            │
└──────────────────────────────────┼────────────────────────────┘
                                   │
                                   ▼ (Transparent proxy)
                    ┌─────────────────────────────┐
                    │  chat.litecoin.com/chat     │  ← Guest Tunnel Endpoint
                    │  (Backstage hallway -       │     (Users never see this)
                    │   users never see this)     │
                    └──────────────┬──────────────┘
                                   │
                                   ▼ (Guest Tunnel)
                    ┌─────────────────────────────┐
                    │  Your Docker Network        │
                    │  frontend:3000              │
                    │  (Next.js with basePath)    │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
            ┌───────────────┐            ┌───────────────┐
            │ api.lite.space│            │ cms.lite.space│
            │   (Backend)   │            │  (Payload)    │
            └───────────────┘            └───────────────┘
```

### Key Points

- **User Experience**: Users see `litecoin.com/chat` in address bar (transparent proxy)
- **Guest Tunnel**: `chat.litecoin.com` is the "backstage hallway" - internal endpoint users never see
- **Worker**: Transparently proxies `litecoin.com/chat*` → `chat.litecoin.com/chat*`
- **basePath**: Next.js configured with `basePath: '/chat'` to handle the path prefix

---

## Related Documentation

- [CORS Cloudflare Configuration](./CORS_CLOUDFLARE_CONFIG.md)
- [Environment Variables](../setup/ENVIRONMENT_VARIABLES.md)
- [Abuse Prevention Stack](../security/ABUSE_PREVENTION_STACK.md) (includes Turnstile details)
- [Capacity Planning](../planning/CAPACITY_PLANNING.md)
