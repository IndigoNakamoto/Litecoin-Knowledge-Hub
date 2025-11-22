# Cloudflare Turnstile Integration Feature

## Overview

This feature integrates **Cloudflare Turnstile** into the Litecoin Knowledge Hub application to provide bot protection and abuse prevention for the chat API endpoints. Turnstile is a privacy-focused alternative to CAPTCHA that provides strong bot protection without user friction.

**Status**: 📋 **Planned** (Documentation Ready)

**Priority**: High - Security and abuse prevention

**Last Updated**: 2025-01-XX

---

## Table of Contents

1. [Feature Summary](#feature-summary)
2. [Security Architecture](#security-architecture)
3. [Business Requirements](#business-requirements)
4. [Technical Requirements](#technical-requirements)
5. [Implementation Details](#implementation-details)
6. [Configuration](#configuration)
7. [Frontend Integration](#frontend-integration)
8. [Backend Integration](#backend-integration)
9. [Testing](#testing)
10. [Deployment](#deployment)
11. [Monitoring](#monitoring)
12. [Troubleshooting](#troubleshooting)
13. [Future Enhancements](#future-enhancements)

---

## Feature Summary

### Problem Statement

Currently, the chat API endpoints are protected by:
- Rate limiting (per-minute and per-hour limits)
- CORS restrictions
- Security headers

However, these measures can be circumvented by sophisticated bots, leading to:
- API abuse and resource exhaustion
- Increased LLM costs from bot requests
- Potential DDoS attacks
- Degraded service quality for legitimate users

### Solution

Integrate **Cloudflare Turnstile** as an additional security layer that:
1. **Validates user interactions** on the frontend before allowing API requests
2. **Verifies Turnstile tokens** on the backend before processing chat requests
3. **Works seamlessly** with existing rate limiting and security measures
4. **Provides transparent verification** without disrupting user experience (invisible mode)

### Key Benefits

- ✅ **Bot Protection** - Effectively blocks automated bots and scrapers
- ✅ **Cost Reduction** - Prevents bot-driven LLM API calls
- ✅ **Better UX** - Invisible verification mode (no user interaction required)
- ✅ **Privacy-Focused** - No tracking or personal data collection
- ✅ **Complements Existing Security** - Works alongside rate limiting and CORS
- ✅ **Configurable** - Can be enabled/disabled per environment

---

## Security Architecture

### Multi-Layer Security Strategy

The application uses a **defense-in-depth** approach with multiple security layers:

```
User Request
    │
    ▼
┌─────────────────────────────────────┐
│ Layer 1: Cloudflare Turnstile       │  ← NEW (Bot protection)
│ - Frontend widget validation        │
│ - Backend token verification        │
│ - Blocks automated requests         │
└──────────────┬──────────────────────┘
               │ Token Verified
               ▼
┌─────────────────────────────────────┐
│ Layer 2: Rate Limiting              │  ← EXISTING (Per-IP limits)
│ - Per-minute limits                 │
│ - Per-hour limits                   │
│ - Progressive penalties             │
└──────────────┬──────────────────────┘
               │ Within Limits
               ▼
┌─────────────────────────────────────┐
│ Layer 3: CORS & Security Headers    │  ← EXISTING (Origin validation)
│ - Origin validation                 │
│ - Security headers                  │
│ - HTTPS enforcement                 │
└──────────────┬──────────────────────┘
               │ Validated
               ▼
┌─────────────────────────────────────┐
│ API Processing                      │
│ - RAG pipeline execution            │
│ - Response generation               │
└─────────────────────────────────────┘
```

### Security Layer Comparison

| Layer | Protection | Scope | Configuration |
|-------|-----------|-------|---------------|
| **Turnstile** | Bot detection & validation | Frontend → Backend | Site key + Secret key |
| **Rate Limiting** | Request frequency limits | Per IP address | Requests per minute/hour |
| **CORS** | Origin validation | Browser requests | Allowed origins list |
| **Security Headers** | Browser security | All responses | CSP, HSTS, etc. |

### Turnstile Verification Flow

```
1. Frontend (User Interaction)
   │
   ├─→ User submits chat message
   ├─→ Turnstile widget generates token (invisible mode)
   └─→ Token included in API request
   
2. Backend (Token Verification)
   │
   ├─→ Receive API request with Turnstile token
   ├─→ Verify token with Cloudflare API
   ├─→ Check verification result
   ├─→ ✅ Success → Process request
   └─→ ❌ Failure → Reject with 403 Forbidden
   
3. Cloudflare (Token Validation)
   │
   ├─→ Backend sends token + secret key
   ├─→ Cloudflare validates token
   ├─→ Checks bot signals, IP reputation, etc.
   └─→ Returns success/failure + metadata
```

### Integration with Existing Security

**Turnstile + Rate Limiting**:
- Turnstile validates user authenticity first
- Rate limiting applies to verified requests
- Bots are blocked before rate limiting counters increment

**Turnstile + CORS**:
- CORS validates request origin
- Turnstile validates request authenticity
- Both must pass for request to proceed

**Error Handling**:
- Turnstile failures return 403 Forbidden (clear rejection)
- Rate limit failures return 429 Too Many Requests (different error)
- System continues to work if Turnstile is disabled (development)

---

## Business Requirements

### BR-1: Bot Protection for Chat Endpoints
- **Requirement**: Protect chat API endpoints from automated bot requests
- **Priority**: Critical
- **Acceptance Criteria**:
  - All chat requests must include valid Turnstile token
  - Invalid or missing tokens are rejected with clear error message
  - Bot requests are blocked before API processing
  - Legitimate user requests are not disrupted

### BR-2: Invisible Verification Mode
- **Requirement**: Use Turnstile in invisible mode for seamless UX
- **Priority**: High
- **Acceptance Criteria**:
  - No user interaction required (no CAPTCHA challenge)
  - Widget appears only when needed (fallback mode)
  - Normal users never see verification challenge
  - Only suspicious traffic sees challenge

### BR-3: Environment-Specific Configuration
- **Requirement**: Enable Turnstile in production, optional in development
- **Priority**: High
- **Acceptance Criteria**:
  - Production: Turnstile required and enforced
  - Development: Turnstile optional (can be disabled)
  - Staging: Turnstile enabled for testing
  - Configuration via environment variables

### BR-4: Graceful Degradation
- **Requirement**: System continues to work if Turnstile verification fails (in development)
- **Priority**: Medium
- **Acceptance Criteria**:
  - Development mode can skip Turnstile verification
  - Production mode strictly enforces verification
  - Clear error messages for verification failures
  - No silent failures in production

### BR-5: Cost Reduction
- **Requirement**: Reduce LLM API costs by blocking bot requests
- **Priority**: High
- **Acceptance Criteria**:
  - Bot requests blocked before LLM processing
  - Reduction in unnecessary API calls
  - Monitoring of blocked requests
  - Cost savings tracking

---

## Technical Requirements

### TR-1: Frontend Turnstile Widget
- **Requirement**: Integrate Turnstile widget in chat interface
- **Priority**: Critical
- **Details**:
  - Load Turnstile script from Cloudflare CDN
  - Render widget in invisible mode
  - Capture token on form submission
  - Include token in API request payload
  - Handle widget errors gracefully

### TR-2: Backend Token Verification
- **Requirement**: Verify Turnstile tokens before processing requests
- **Priority**: Critical
- **Details**:
  - Send token to Cloudflare verification API
  - Include client IP address in verification
  - Validate verification response
  - Reject requests with invalid tokens
  - Log verification failures for monitoring

### TR-3: API Payload Updates
- **Requirement**: Include Turnstile token in chat API requests
- **Priority**: Critical
- **Details**:
  - Update `ChatRequest` model to include `turnstile_token` field
  - Frontend sends token in request body
  - Backend extracts token from request
  - Optional field (can be None in development)

### TR-4: Error Handling
- **Requirement**: Proper error handling for Turnstile failures
- **Priority**: High
- **Details**:
  - Clear error messages for verification failures
  - Differentiate between missing token and invalid token
  - Log errors for debugging
  - Return appropriate HTTP status codes (403 Forbidden)

### TR-5: Configuration Management
- **Requirement**: Environment-based configuration
- **Priority**: High
- **Details**:
  - Site key for frontend (public)
  - Secret key for backend (private)
  - Enable/disable flag per environment
  - Configuration via environment variables

---

## Implementation Details

### File Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Turnstile.tsx              # NEW: Turnstile widget component
│   │   └── InputBox.tsx               # MODIFIED: Add Turnstile integration
│   └── app/
│       └── page.tsx                   # MODIFIED: Pass token to API

backend/
├── utils/
│   └── turnstile.py                   # NEW: Token verification utility
├── data_models.py                     # MODIFIED: Add turnstile_token field
└── main.py                            # MODIFIED: Verify token in endpoints
```

### Frontend Components

#### `Turnstile.tsx` (NEW)

React component for Cloudflare Turnstile widget:

```tsx
'use client';

import { useEffect, useRef, useState } from 'react';

declare global {
  interface Window {
    turnstile: {
      render: (
        element: string | HTMLElement,
        options: {
          sitekey: string;
          callback?: (token: string) => void;
          'error-callback'?: () => void;
          'expired-callback'?: () => void;
          theme?: 'light' | 'dark' | 'auto';
          size?: 'normal' | 'compact';
        }
      ) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
    };
  }
}

interface TurnstileProps {
  siteKey: string;
  onVerify: (token: string) => void;
  onError?: () => void;
  theme?: 'light' | 'dark' | 'auto';
  size?: 'normal' | 'compact';
}

export default function Turnstile({
  siteKey,
  onVerify,
  onError,
  theme = 'auto',
  size = 'normal',
}: TurnstileProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load Turnstile script
  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
    script.async = true;
    script.defer = true;
    script.onload = () => setIsLoaded(true);
    document.body.appendChild(script);

    return () => {
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
      }
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  // Render widget when script loads
  useEffect(() => {
    if (isLoaded && containerRef.current && window.turnstile && !widgetIdRef.current) {
      widgetIdRef.current = window.turnstile.render(containerRef.current, {
        sitekey: siteKey,
        callback: (token) => onVerify(token),
        'error-callback': () => onError?.(),
        'expired-callback': () => {
          if (widgetIdRef.current) {
            window.turnstile.reset(widgetIdRef.current);
          }
        },
        theme,
        size,
      });
    }

    return () => {
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
    };
  }, [isLoaded, siteKey, onVerify, onError, theme, size]);

  return <div ref={containerRef} />;
}
```

**Key Features**:
- Dynamic script loading from Cloudflare CDN
- Automatic widget lifecycle management
- Token callback handling
- Error and expiration handling
- Widget cleanup on unmount

#### `InputBox.tsx` (MODIFIED)

Update to integrate Turnstile widget:

```tsx
import Turnstile from './Turnstile';
import { useState } from 'react';

interface InputBoxProps {
  onSendMessage: (message: string, turnstileToken: string) => void;
  isLoading: boolean;
}

const InputBox: React.FC<InputBoxProps> = ({ onSendMessage, isLoading }) => {
  const [input, setInput] = useState("");
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [turnstileError, setTurnstileError] = useState(false);

  const handleSend = () => {
    if (input.trim() && !isLoading && turnstileToken) {
      onSendMessage(input, turnstileToken);
      setInput("");
      setTurnstileToken(null); // Reset token after sending
      // Reset widget
      // ... widget reset logic
    }
  };

  const handleTurnstileVerify = (token: string) => {
    setTurnstileToken(token);
    setTurnstileError(false);
  };

  const handleTurnstileError = () => {
    setTurnstileToken(null);
    setTurnstileError(true);
  };

  const turnstileSiteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || '';

  return (
    <div className="sticky bottom-0 inset-x-0 z-10 bg-background/80 backdrop-blur-sm">
      {/* ... existing input box UI ... */}
      
      {/* Add Turnstile widget (invisible mode) */}
      {turnstileSiteKey && (
        <div className="hidden"> {/* Hidden in invisible mode */}
          <Turnstile
            siteKey={turnstileSiteKey}
            onVerify={handleTurnstileVerify}
            onError={handleTurnstileError}
            theme="auto"
            size="compact"
          />
        </div>
      )}
      
      {/* Show error message if verification fails */}
      {turnstileError && (
        <p className="text-sm text-red-500 mt-2 px-4">
          Verification failed. Please try again.
        </p>
      )}
    </div>
  );
};
```

**Key Changes**:
- Track Turnstile token state
- Pass token to `onSendMessage` callback
- Handle verification success/error
- Reset token after message sent
- Show error message if verification fails

### Backend Components

#### `utils/turnstile.py` (NEW)

Utility for Turnstile token verification:

```python
import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

def is_turnstile_enabled() -> bool:
    """Check if Turnstile verification is enabled."""
    return os.getenv("ENABLE_TURNSTILE", "false").lower() == "true"

async def verify_turnstile_token(
    token: str, 
    remoteip: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify a Cloudflare Turnstile token.
    
    Args:
        token: The Turnstile token from the frontend
        remoteip: Optional client IP address for verification
        
    Returns:
        Dict with 'success' (bool) and other verification details
    """
    # Check if Turnstile is enabled
    if not is_turnstile_enabled():
        logger.debug("Turnstile verification disabled, skipping check")
        return {"success": True, "skip": True}
    
    if not TURNSTILE_SECRET_KEY:
        logger.warning("TURNSTILE_SECRET_KEY not configured, skipping Turnstile verification")
        return {"success": True, "skip": True}
    
    if not token:
        logger.warning("Turnstile token missing in request")
        return {"success": False, "error": "missing_token"}
    
    try:
        data = {
            "secret": TURNSTILE_SECRET_KEY,
            "response": token,
        }
        if remoteip:
            data["remoteip"] = remoteip
        
        response = requests.post(TURNSTILE_VERIFY_URL, data=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get("success", False):
            error_codes = result.get("error-codes", [])
            logger.warning(
                f"Turnstile verification failed: {error_codes}, "
                f"IP: {remoteip or 'unknown'}"
            )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error verifying Turnstile token: {e}", exc_info=True)
        return {"success": False, "error": "verification_error"}
    except Exception as e:
        logger.error(f"Unexpected error verifying Turnstile token: {e}", exc_info=True)
        return {"success": False, "error": "unexpected_error"}
```

**Key Features**:
- Environment-based enable/disable
- Token verification with Cloudflare API
- IP address inclusion for enhanced validation
- Comprehensive error handling
- Detailed logging for monitoring

#### `data_models.py` (MODIFIED)

Update `ChatRequest` model:

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=400)
    chat_history: List[ChatMessage] = Field(default_factory=list)
    turnstile_token: Optional[str] = None  # NEW: Turnstile token
```

**Key Changes**:
- Add optional `turnstile_token` field
- Field can be None (for development mode)

#### `main.py` (MODIFIED)

Update chat endpoints to verify Turnstile token:

```python
from backend.utils.turnstile import verify_turnstile_token, is_turnstile_enabled

@app.post("/api/v1/chat/stream")
async def chat_stream_endpoint(
    request: ChatRequest, 
    background_tasks: BackgroundTasks, 
    http_request: Request
):
    """
    Streaming endpoint for chat queries with real-time response delivery.
    Returns Server-Sent Events with incremental chunks of the response.
    """
    # Rate limiting
    await check_rate_limit(http_request, STREAM_RATE_LIMIT)
    
    # Verify Turnstile token (if enabled)
    if is_turnstile_enabled():
        client_ip = http_request.client.host if http_request.client else None
        turnstile_result = await verify_turnstile_token(
            request.turnstile_token or "",
            remoteip=client_ip
        )
        
        if not turnstile_result.get("success", False):
            logger.warning(
                f"Turnstile verification failed for request from {client_ip}: "
                f"{turnstile_result.get('error-codes', [])}"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Verification failed",
                    "message": "Please complete the security verification and try again."
                }
            )
    
    # Continue with existing request processing...
    # ... rest of endpoint logic
```

**Key Changes**:
- Check if Turnstile is enabled
- Verify token before processing
- Reject with 403 Forbidden if verification fails
- Include client IP in verification
- Log verification failures

---

## Configuration

### Environment Variables

#### Frontend Configuration

Add to `frontend/.env.local` or root `.env.local`:

```bash
# Cloudflare Turnstile Site Key (public, safe to expose)
NEXT_PUBLIC_TURNSTILE_SITE_KEY=your_site_key_here
```

**Where to set:**
- Development: `frontend/.env.local` or root `.env.local`
- Docker Development: Root `.env.docker.dev`
- Docker Production: Root `.env.docker.prod`

#### Backend Configuration

Add to `backend/.env`:

```bash
# Cloudflare Turnstile Secret Key (private, never expose)
TURNSTILE_SECRET_KEY=your_secret_key_here

# Enable/disable Turnstile verification (default: false)
ENABLE_TURNSTILE=false  # Set to "true" in production
```

**Where to set:**
- All environments: `backend/.env`

### Configuration by Environment

| Environment | Enable Turnstile | Site Key | Secret Key | Purpose |
|-------------|------------------|----------|------------|---------|
| **Development** | `false` | Optional | Optional | Local testing without verification |
| **Staging** | `true` | Required | Required | Test verification flow |
| **Production** | `true` | Required | Required | Enforce bot protection |

### Getting Cloudflare Turnstile Keys

1. **Log in to Cloudflare Dashboard**:
   - Go to https://dash.cloudflare.com
   - Navigate to your account

2. **Access Turnstile**:
   - Go to **Security** → **Turnstile**
   - Click **Add Site** or select existing site

3. **Configure Site**:
   - **Site Name**: Litecoin Knowledge Hub Chat
   - **Domain**: `chat.lite.space` (or your domain)
   - **Widget Mode**: **Invisible** (recommended for seamless UX)
   - **Pre-Clearance**: Optional (for faster verification)

4. **Copy Keys**:
   - **Site Key**: Public key for frontend (starts with `0x`)
   - **Secret Key**: Private key for backend (starts with `0x`)

5. **Configure Environment Variables**:
   ```bash
   # Frontend
   NEXT_PUBLIC_TURNSTILE_SITE_KEY=0x...your_site_key
   
   # Backend
   TURNSTILE_SECRET_KEY=0x...your_secret_key
   ENABLE_TURNSTILE=true
   ```

### Widget Mode Options

**Invisible Mode** (Recommended):
- No user interaction required
- Automatic verification in background
- Challenge shown only for suspicious traffic
- Best UX for legitimate users

**Non-Interactive Mode**:
- Shows widget but no challenge
- Automatic verification
- Visible to users (small widget)

**Interactive Mode**:
- Shows challenge if needed
- User interaction required for verification
- More secure but worse UX

**Recommendation**: Use **Invisible Mode** for best user experience.

---

## Frontend Integration

### Component Integration Steps

1. **Install/Import Turnstile Component**:
   ```tsx
   import Turnstile from '@/components/Turnstile';
   ```

2. **Add to Chat Form**:
   ```tsx
   {turnstileSiteKey && (
     <Turnstile
       siteKey={turnstileSiteKey}
       onVerify={handleTurnstileVerify}
       onError={handleTurnstileError}
       theme="auto"
       size="compact"
     />
   )}
   ```

3. **Handle Token State**:
   ```tsx
   const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
   
   const handleTurnstileVerify = (token: string) => {
     setTurnstileToken(token);
   };
   ```

4. **Include Token in API Request**:
   ```tsx
   const response = await fetch(`${backendUrl}/api/v1/chat/stream`, {
     method: "POST",
     headers: {
       "Content-Type": "application/json",
     },
     body: JSON.stringify({ 
       query: message, 
       chat_history: history,
       turnstile_token: turnstileToken  // Include token
     }),
   });
   ```

5. **Reset Token After Request**:
   ```tsx
   // After successful request, reset token
   setTurnstileToken(null);
   // Widget will generate new token for next request
   ```

### Token Lifecycle

```
1. User opens chat interface
   │
   ├─→ Turnstile widget initializes (invisible)
   ├─→ Widget generates token automatically
   └─→ Token stored in component state
   
2. User submits message
   │
   ├─→ Token included in API request
   ├─→ Backend verifies token
   └─→ Request processed if verified
   
3. After request completes
   │
   ├─→ Token cleared from state
   ├─→ Widget generates new token
   └─→ Ready for next request
```

### Error Handling

**Verification Errors**:
- Show user-friendly error message
- Allow retry (widget will regenerate token)
- Log error for debugging

**Widget Loading Errors**:
- Fallback to showing widget in visible mode
- Allow manual verification if automatic fails

**Network Errors**:
- Handle gracefully (don't block user)
- In development, may skip verification if disabled

---

## Backend Integration

### Endpoint Protection

Protect chat endpoints with Turnstile verification:

```python
@app.post("/api/v1/chat/stream")
async def chat_stream_endpoint(
    request: ChatRequest, 
    background_tasks: BackgroundTasks, 
    http_request: Request
):
    # 1. Rate limiting (existing)
    await check_rate_limit(http_request, STREAM_RATE_LIMIT)
    
    # 2. Turnstile verification (new)
    if is_turnstile_enabled():
        client_ip = http_request.client.host if http_request.client else None
        turnstile_result = await verify_turnstile_token(
            request.turnstile_token or "",
            remoteip=client_ip
        )
        
        if not turnstile_result.get("success", False):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Verification failed",
                    "message": "Please complete the security verification and try again."
                }
            )
    
    # 3. Process request (existing)
    # ... rest of endpoint logic
```

### Verification Order

1. **Rate Limiting** (first)
   - Applies to all requests
   - Blocks excessive requests early

2. **Turnstile Verification** (second)
   - Validates request authenticity
   - Blocks bot requests

3. **CORS Validation** (already handled by middleware)
   - Validates request origin

4. **Request Processing** (last)
   - Only reached if all validations pass

### Error Responses

**Missing Token**:
```json
{
  "error": "Verification failed",
  "message": "Please complete the security verification and try again."
}
```
Status: `403 Forbidden`

**Invalid Token**:
```json
{
  "error": "Verification failed",
  "message": "Please complete the security verification and try again."
}
```
Status: `403 Forbidden`

**Verification Error** (network/timeout):
- Log error internally
- Return same error message (don't expose internal errors)

---

## Testing

### Unit Tests

**Turnstile Verification**:
- Test token verification with valid token
- Test token verification with invalid token
- Test missing token handling
- Test network error handling
- Test enable/disable flag

**Frontend Components**:
- Test widget initialization
- Test token callback
- Test error handling
- Test widget reset

### Integration Tests

**End-to-End Flow**:
1. Frontend: Generate Turnstile token
2. Frontend: Include token in API request
3. Backend: Verify token
4. Backend: Process request if verified
5. Backend: Reject request if invalid

**Error Scenarios**:
- Missing token in request
- Invalid token
- Expired token
- Network error during verification
- Turnstile disabled (should skip)

### Manual Testing

**Development Mode** (Turnstile disabled):
```bash
# Set in backend/.env
ENABLE_TURNSTILE=false

# Should allow requests without token
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}'
# Should work without token
```

**Production Mode** (Turnstile enabled):
```bash
# Set in backend/.env
ENABLE_TURNSTILE=true
TURNSTILE_SECRET_KEY=your_secret_key

# Without token - should fail
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": []}'
# Should return 403 Forbidden

# With valid token - should work
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "chat_history": [], "turnstile_token": "valid_token"}'
# Should process request
```

### Test Cases

| Test Case | Expected Behavior |
|-----------|-------------------|
| Valid token | Request processed successfully |
| Missing token (enabled) | 403 Forbidden error |
| Invalid token | 403 Forbidden error |
| Expired token | 403 Forbidden error |
| Network error | 403 Forbidden error (logged) |
| Turnstile disabled | Request processed (skip verification) |
| Bot request | 403 Forbidden (blocked by Turnstile) |
| Legitimate user | Request processed successfully |

---

## Deployment

### Prerequisites

1. **Cloudflare Account**:
   - Sign up at https://dash.cloudflare.com
   - Access Turnstile section

2. **Turnstile Site Configuration**:
   - Create site in Cloudflare dashboard
   - Get Site Key and Secret Key
   - Configure domain(s)

3. **Environment Variables**:
   - Frontend: `NEXT_PUBLIC_TURNSTILE_SITE_KEY`
   - Backend: `TURNSTILE_SECRET_KEY`
   - Backend: `ENABLE_TURNSTILE=true` (production)

### Deployment Steps

#### 1. Configure Cloudflare Turnstile

1. Log in to Cloudflare Dashboard
2. Navigate to **Security** → **Turnstile**
3. Click **Add Site**
4. Configure:
   - **Site Name**: Litecoin Knowledge Hub
   - **Domain**: `chat.lite.space` (or your domain)
   - **Widget Mode**: Invisible
5. Copy **Site Key** and **Secret Key**

#### 2. Set Environment Variables

**Frontend** (`.env.docker.prod` or production environment):
```bash
NEXT_PUBLIC_TURNSTILE_SITE_KEY=0x...your_site_key
```

**Backend** (`backend/.env`):
```bash
TURNSTILE_SECRET_KEY=0x...your_secret_key
ENABLE_TURNSTILE=true
```

#### 3. Deploy Code Changes

1. **Frontend**:
   ```bash
   # Build frontend with new environment variable
   cd frontend
   npm run build
   # Deploy frontend
   ```

2. **Backend**:
   ```bash
   # Deploy backend with Turnstile verification
   # Restart backend service
   ```

#### 4. Verify Deployment

1. **Check Frontend**:
   - Open browser console
   - Verify Turnstile script loads
   - Check for widget initialization

2. **Check Backend**:
   - Test API endpoint with valid token
   - Test API endpoint without token (should fail)
   - Check logs for verification messages

3. **Test End-to-End**:
   - Submit chat message from frontend
   - Verify request succeeds
   - Check backend logs for verification

#### 5. Monitor Performance

1. **Check Error Rates**:
   - Monitor 403 Forbidden responses
   - Track verification failures

2. **Check Blocked Requests**:
   - Review Cloudflare Turnstile dashboard
   - Check blocked bot requests

3. **Monitor Costs**:
   - Track reduction in bot-driven API calls
   - Monitor LLM cost savings

### Rollback Plan

If issues occur:

1. **Disable Turnstile** (immediate):
   ```bash
   # In backend/.env
   ENABLE_TURNSTILE=false
   # Restart backend
   ```

2. **Remove Frontend Widget** (optional):
   - Remove Turnstile component from InputBox
   - Remove token from API request

3. **Revert Code** (if needed):
   - Revert backend changes
   - Revert frontend changes
   - System returns to pre-Turnstile state

**Note**: Rollback is safe and immediate - no data loss.

---

## Monitoring

### Metrics to Track

#### Turnstile Verification Metrics

**Success Rate**:
- Percentage of successful verifications
- Should be >95% for legitimate users

**Failure Reasons**:
- Missing token
- Invalid token
- Network errors
- Cloudflare API errors

**Blocked Requests**:
- Number of requests blocked by Turnstile
- Percentage of total requests

#### Cost Impact Metrics

**API Call Reduction**:
- Number of bot requests blocked
- Reduction in LLM API calls
- Cost savings from blocked requests

### Logging

**Turnstile Verification Logs**:
```
# Successful verification
INFO: Turnstile verification successful for IP: 192.168.1.1

# Failed verification
WARNING: Turnstile verification failed for IP: 192.168.1.2: ['invalid-input-response']

# Missing token
WARNING: Turnstile token missing in request from IP: 192.168.1.3

# Network error
ERROR: Error verifying Turnstile token: Connection timeout
```

**Monitoring Queries** (if using structured logging):
```python
# Count verification failures
turnstile_verification_failures_total

# Count verification successes
turnstile_verification_successes_total

# Verification duration
turnstile_verification_duration_seconds
```

### Cloudflare Dashboard

**Turnstile Analytics**:
- Access via Cloudflare Dashboard → Security → Turnstile
- View:
  - Total challenges
  - Pass rate
  - Blocked requests
  - Geographic distribution

### Alerting

**Recommended Alerts**:
- High verification failure rate (>10%)
- Unusual spike in blocked requests
- Turnstile API errors

---

## Troubleshooting

### Common Issues

#### Issue: Turnstile Widget Not Loading

**Symptoms**:
- Widget doesn't appear
- Console errors about Turnstile script

**Solutions**:
1. Check Site Key is set correctly:
   ```bash
   echo $NEXT_PUBLIC_TURNSTILE_SITE_KEY
   ```

2. Verify script loads:
   - Check browser console for errors
   - Verify script URL is accessible

3. Check CORS (if applicable):
   - Ensure Cloudflare CDN is accessible
   - Check network firewall rules

#### Issue: Verification Always Fails

**Symptoms**:
- All requests return 403 Forbidden
- Legitimate users blocked

**Solutions**:
1. Verify Secret Key:
   ```bash
   # Check backend/.env
   grep TURNSTILE_SECRET_KEY backend/.env
   ```

2. Check Site Key and Secret Key match:
   - Both must be from same Turnstile site
   - Keys are paired - can't mix different sites

3. Verify domain configuration:
   - Check Cloudflare Turnstile dashboard
   - Ensure domain matches your site

4. Check IP address:
   - Verify client IP is passed correctly
   - Some proxies may hide real IP

#### Issue: Token Expired

**Symptoms**:
- Initial request works
- Subsequent requests fail
- "Token expired" errors

**Solutions**:
1. Reset widget after each request:
   ```tsx
   // After successful request
   setTurnstileToken(null);
   // Widget will generate new token
   ```

2. Handle token expiration:
   ```tsx
   'expired-callback': () => {
     // Reset widget to get new token
     if (widgetIdRef.current) {
       window.turnstile.reset(widgetIdRef.current);
     }
   }
   ```

#### Issue: Turnstile Disabled But Still Enforced

**Symptoms**:
- Requests fail even with `ENABLE_TURNSTILE=false`
- Verification still runs

**Solutions**:
1. Check environment variable:
   ```bash
   # Verify in backend/.env
   ENABLE_TURNSTILE=false  # Must be exactly "false"
   ```

2. Restart backend service:
   ```bash
   # Environment variables only load on startup
   # Restart to apply changes
   ```

3. Check variable parsing:
   ```python
   # Should be case-insensitive
   return os.getenv("ENABLE_TURNSTILE", "false").lower() == "true"
   ```

#### Issue: High False Positive Rate

**Symptoms**:
- Legitimate users blocked
- High verification failure rate

**Solutions**:
1. Adjust Turnstile settings:
   - Use "Invisible" mode (more lenient)
   - Enable "Pre-Clearance" (faster verification)

2. Check IP reputation:
   - Some IP ranges may be flagged
   - VPN users may have issues

3. Review Cloudflare dashboard:
   - Check pass rate metrics
   - Adjust sensitivity if available

### Debugging Steps

1. **Enable Debug Logging**:
   ```python
   # In backend/.env
   LOG_LEVEL=DEBUG
   ```

2. **Check Verification Response**:
   ```python
   # Log full verification result
   logger.debug(f"Turnstile verification result: {turnstile_result}")
   ```

3. **Test Token Manually**:
   ```bash
   # Test verification endpoint directly
   curl -X POST https://challenges.cloudflare.com/turnstile/v0/siteverify \
     -d "secret=YOUR_SECRET_KEY" \
     -d "response=TOKEN_TO_TEST"
   ```

4. **Verify Widget State**:
   ```tsx
   // Check token state in browser console
   console.log('Turnstile token:', turnstileToken);
   ```

---

## Future Enhancements

### Phase 2: Advanced Configuration

- **Custom Challenge Thresholds**: Adjust sensitivity per endpoint
- **Per-User Verification**: Skip verification for authenticated users
- **Geographic Rules**: Different rules per region
- **Rate Limit Integration**: Combine with existing rate limiting

### Phase 3: Analytics & Reporting

- **Dashboard Integration**: Add Turnstile metrics to Grafana
- **Cost Tracking**: Track cost savings from blocked requests
- **Bot Pattern Analysis**: Identify common bot behaviors
- **Performance Metrics**: Monitor verification latency

### Phase 4: Adaptive Security

- **Risk Scoring**: Dynamic verification based on risk level
- **User Reputation**: Remember verified users
- **Progressive Challenges**: Escalate only when needed
- **Machine Learning**: Learn from past verification patterns

---

## Related Documentation

- [Advanced Abuse Prevention](./FEATURE_ADVANCED_ABUSE_PREVENTION.md) - **Enhanced security integration** that combines Turnstile with challenge-response fingerprinting and advanced protections
- [Client-Side Fingerprinting](./FEATURE_CLIENT_FINGERPRINTING.md) - Fingerprinting feature that works with Turnstile
- [Environment Variables](./ENVIRONMENT_VARIABLES.md) - Environment variable configuration
- [Rate Limiting](../backend/rate_limiter.py) - Existing rate limiting implementation
- [Security Headers](../backend/middleware/security_headers.py) - Security headers middleware
- [Cloudflare Turnstile Documentation](https://developers.cloudflare.com/turnstile/) - Official Turnstile docs
- [RED_TEAM_ASSESSMENT_COMBINED.md](./RED_TEAM_ASSESSMENT_COMBINED.md) - Security assessment

---

## Changelog

### 2025-01-XX - Feature Documentation
- Created feature documentation for Cloudflare Turnstile integration
- Documented frontend and backend implementation approach
- Added configuration and deployment guides
- Included troubleshooting and monitoring sections

---

**Document Status**: 📋 **Documentation Ready** (Implementation Pending)

