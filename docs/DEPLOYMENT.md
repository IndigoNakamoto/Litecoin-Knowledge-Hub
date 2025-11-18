# Deployment Guide

This guide covers deploying all three components of the Litecoin Knowledge Hub:
1. **Frontend** (Next.js)
2. **Backend** (FastAPI)
3. **Payload CMS** (Next.js)

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Frontend Deployment (Next.js)](#frontend-deployment-nextjs)
- [Backend Deployment (FastAPI)](#backend-deployment-fastapi)
- [Payload CMS Deployment](#payload-cms-deployment)
- [Docker Deployment (All Services)](#docker-deployment-all-services)
- [Post-Deployment Checklist](#post-deployment-checklist)

---

## Prerequisites

Before deploying, ensure you have:

1. **Production MongoDB Database**
   - MongoDB Atlas cluster (recommended) or self-hosted MongoDB instance
   - Connection string with appropriate credentials
   - Database name: `litecoin_rag_db` (or configure via env vars)

2. **Google AI API Key**
   - Required for embeddings and LLM generation
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

3. **Domain Names (Optional)**
   - Custom domain for frontend (e.g., `knowledgehub.litecoin.org`)
   - Custom domain for backend API (e.g., `api.litecoin.org`)
   - Custom domain for CMS (e.g., `cms.litecoin.org`)

4. **Deployment Platforms**
   - **Frontend**: Vercel (recommended) or any Next.js hosting
   - **Backend**: Railway, Render, Fly.io, or any Python hosting with Docker support
   - **Payload CMS**: Vercel, Railway, Render, or Docker container

---

## Environment Variables

### Backend Environment Variables

Create a `.env` file in the `backend/` directory or set these in your deployment platform:

```env
# MongoDB Configuration
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/litecoin_rag_db?retryWrites=true&w=majority
MONGO_DB_NAME=litecoin_rag_db
MONGO_COLLECTION_NAME=litecoin_docs

# MongoDB for CMS sync (can be same as above)
MONGO_DETAILS=mongodb+srv://username:password@cluster.mongodb.net/litecoin_rag_db?retryWrites=true&w=majority
MONGO_DATABASE_NAME=litecoin_rag_db
CMS_ARTICLES_COLLECTION_NAME=cms_articles

# Google AI API
GOOGLE_API_KEY=your-google-api-key-here

# Webhook Secret (must match Payload CMS WEBHOOK_SECRET)
# Generate with: openssl rand -base64 32
WEBHOOK_SECRET=your-webhook-secret-here

# Embedding Model (optional, defaults to text-embedding-004)
EMBEDDING_MODEL=text-embedding-004

# FAISS Index Path (for local development, not needed in production with MongoDB Atlas)
# FAISS_INDEX_PATH=./backend/faiss_index

# CORS Origins (comma-separated list of allowed origins)
# For production, replace with your frontend domain
CORS_ORIGINS=https://your-frontend-domain.com,https://www.your-frontend-domain.com
```

### Frontend Environment Variables

Set these in your deployment platform (Vercel, etc.):

```env
# Backend API URL
NEXT_PUBLIC_BACKEND_URL=https://your-backend-api-domain.com

# Optional: Analytics, etc.
NEXT_PUBLIC_APP_NAME=Litecoin Knowledge Hub
```

### Payload CMS Environment Variables

Create a `.env` file in the `payload_cms/` directory or set these in your deployment platform:

```env
# MongoDB Connection
DATABASE_URI=mongodb+srv://username:password@cluster.mongodb.net/payload_cms?retryWrites=true&w=majority

# Payload Secret (generate a secure random string)
PAYLOAD_SECRET=your-secure-random-secret-key-here

# Server URL (where Payload CMS will be accessible)
PAYLOAD_PUBLIC_SERVER_URL=https://your-cms-domain.com

# Backend URL (for webhook sync)
BACKEND_URL=https://your-backend-api-domain.com

# Webhook Secret (must match backend WEBHOOK_SECRET)
# Generate with: openssl rand -base64 32
WEBHOOK_SECRET=your-webhook-secret-here

# Node Environment
NODE_ENV=production
```

**Generate a secure PAYLOAD_SECRET:**
```bash
# Using OpenSSL
openssl rand -base64 32

# Or using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

---

## Frontend Deployment (Next.js)

### Option 1: Vercel (Recommended)

1. **Install Vercel CLI** (optional, you can also use the web interface):
   ```bash
   npm i -g vercel
   ```

2. **Deploy:**
   ```bash
   cd frontend
   vercel
   ```

3. **Configure Environment Variables:**
   - Go to your project settings in Vercel dashboard
   - Add `NEXT_PUBLIC_BACKEND_URL` with your backend API URL

4. **Update next.config.ts for Production:**
   Update `frontend/next.config.ts` to use production backend URL:
   ```typescript
   const nextConfig: NextConfig = {
     async rewrites() {
       return [
         {
           source: '/api/v1/:path*',
           destination: process.env.NEXT_PUBLIC_BACKEND_URL + '/api/v1/:path*',
         },
       ]
     },
   }
   ```

### Option 2: Docker Deployment

See [Docker Deployment](#docker-deployment-all-services) section below.

### Option 3: Other Platforms (Railway, Render, etc.)

1. Connect your repository
2. Set build command: `npm run build`
3. Set start command: `npm start`
4. Configure environment variables
5. Deploy

---

## Backend Deployment (FastAPI)

### Option 1: Railway (Recommended for Python)

1. **Install Railway CLI:**
   ```bash
   npm i -g @railway/cli
   ```

2. **Login and Initialize:**
   ```bash
   railway login
   cd backend
   railway init
   ```

3. **Configure Environment Variables:**
   ```bash
   railway variables set MONGO_URI="your-mongodb-connection-string"
   railway variables set GOOGLE_API_KEY="your-google-api-key"
   # Add all other required environment variables
   ```

4. **Deploy:**
   ```bash
   railway up
   ```

5. **Configure Startup Command:**
   - Platform: Python
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Option 2: Render

1. **Create a new Web Service:**
   - Connect your GitHub repository
   - Root Directory: `backend`
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

2. **Add Environment Variables:**
   - Add all required environment variables in the Render dashboard

### Option 3: Fly.io

1. **Install Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Initialize:**
   ```bash
   cd backend
   fly launch
   ```

3. **Configure:**
   - Follow the prompts to set up your app
   - Add environment variables: `fly secrets set MONGO_URI="..." GOOGLE_API_KEY="..."`

4. **Deploy:**
   ```bash
   fly deploy
   ```

### Option 4: Docker Deployment

See [Docker Deployment](#docker-deployment-all-services) section below.

### Important: Update CORS Settings

In `backend/main.py`, update the CORS origins for production:

```python
origins = [
    "https://your-frontend-domain.com",
    "https://www.your-frontend-domain.com",
]

# Or use environment variable
import os
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
```

---

## Payload CMS Deployment

### Option 1: Vercel

1. **Deploy:**
   ```bash
   cd payload_cms
   vercel
   ```

2. **Configure Environment Variables:**
   - `DATABASE_URI`: MongoDB connection string
   - `PAYLOAD_SECRET`: Secure random secret
   - `PAYLOAD_PUBLIC_SERVER_URL`: Your CMS domain
   - `BACKEND_URL`: Your backend API URL
   - `NODE_ENV`: `production`

3. **Build Settings:**
   - Framework Preset: Next.js
   - Build Command: `pnpm build` (or `npm run build`)
   - Output Directory: `.next`

### Option 2: Railway

1. **Initialize:**
   ```bash
   cd payload_cms
   railway init
   ```

2. **Configure:**
   - Set environment variables
   - Build Command: `pnpm install && pnpm build`
   - Start Command: `pnpm start`

3. **Deploy:**
   ```bash
   railway up
   ```

### Option 3: Docker Deployment

See [Docker Deployment](#docker-deployment-all-services) section below.

### Important: Update next.config.mjs for Production

Ensure `payload_cms/next.config.mjs` has standalone output for Docker:

```javascript
import { withPayload } from '@payloadcms/next/withPayload'

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // Required for Docker deployment
}

export default withPayload(nextConfig, { devBundleServerPackages: false })
```

---

## Docker Deployment (All Services)

### Backend Dockerfile

A `Dockerfile` is provided in `backend/Dockerfile`. If not, create one:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
FROM node:22-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
```

Update `frontend/next.config.ts`:

```typescript
const nextConfig: NextConfig = {
  output: 'standalone', // Required for Docker
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: process.env.NEXT_PUBLIC_BACKEND_URL + '/api/v1/:path*',
      },
    ]
  },
}
```

### Docker Compose (All Services)

Create `docker-compose.prod.yml` in the project root:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - MONGO_URI=${MONGO_URI}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - MONGO_DB_NAME=${MONGO_DB_NAME:-litecoin_rag_db}
      - MONGO_COLLECTION_NAME=${MONGO_COLLECTION_NAME:-litecoin_docs}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000}
    env_file:
      - ./backend/.env
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL:-http://localhost:8000}
    depends_on:
      - backend
    restart: unless-stopped

  payload_cms:
    build:
      context: ./payload_cms
      dockerfile: Dockerfile
    ports:
      - "3001:3000"
    environment:
      - DATABASE_URI=${DATABASE_URI}
      - PAYLOAD_SECRET=${PAYLOAD_SECRET}
      - PAYLOAD_PUBLIC_SERVER_URL=${PAYLOAD_PUBLIC_SERVER_URL:-http://localhost:3001}
      - BACKEND_URL=${BACKEND_URL:-http://localhost:8000}
      - NODE_ENV=production
    env_file:
      - ./payload_cms/.env
    depends_on:
      - backend
    restart: unless-stopped
```

**Deploy with Docker Compose:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Post-Deployment Checklist

After deploying all services, verify the following:

### 1. Backend Health Check
```bash
curl https://your-backend-domain.com/
# Should return: {"Hello": "World"}
```

### 2. Frontend Accessibility
- Visit your frontend URL
- Verify the UI loads correctly
- Test API connectivity

### 3. Payload CMS Admin Panel
- Visit `https://your-cms-domain.com/admin`
- Login with admin credentials
- Verify content collections are accessible

### 4. Webhook Synchronization
- Create a test article in Payload CMS
- Publish it
- Verify it syncs to the backend (check `/api/v1/sources`)
- Query the RAG pipeline to confirm the article is indexed

### 5. RAG Pipeline Test
```bash
curl -X POST https://your-backend-domain.com/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Litecoin?",
    "chat_history": []
  }'
```

### 6. CORS Configuration
- Verify frontend can make requests to backend
- Check browser console for CORS errors

### 7. Environment Variables
- Verify all environment variables are set correctly
- Check that sensitive data (API keys, secrets) are not exposed

### 8. Monitoring & Logging
- Set up monitoring (e.g., Sentry, LogRocket)
- Configure log aggregation
- Set up alerts for errors

---

## Troubleshooting

### Backend Issues

**Issue: MongoDB connection fails**
- Verify `MONGO_URI` is correct
- Check MongoDB Atlas IP whitelist (if using Atlas)
- Ensure database user has proper permissions

**Issue: CORS errors**
- Update `origins` in `backend/main.py` with production frontend URL
- Or use `CORS_ORIGINS` environment variable

**Issue: FAISS index not found**
- In production with MongoDB Atlas, FAISS is not needed (vector search uses Atlas)
- Remove `FAISS_INDEX_PATH` from environment variables

### Frontend Issues

**Issue: API requests fail**
- Verify `NEXT_PUBLIC_BACKEND_URL` is set correctly
- Check `next.config.ts` rewrites configuration
- Verify backend CORS allows frontend origin

### Payload CMS Issues

**Issue: Cannot connect to database**
- Verify `DATABASE_URI` is correct
- Check MongoDB connection from CMS server location

**Issue: Webhooks not syncing**
- Verify `BACKEND_URL` in Payload CMS environment
- Check backend `/api/v1/sync/payload` endpoint is accessible
- Review Payload CMS webhook logs

---

## Additional Resources

- [Vercel Deployment Docs](https://vercel.com/docs)
- [Railway Deployment Docs](https://docs.railway.app/)
- [Render Deployment Docs](https://render.com/docs)
- [Fly.io Deployment Docs](https://fly.io/docs/)
- [Payload CMS Deployment](https://payloadcms.com/docs/deployment/overview)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

## Support

For deployment issues, please:
1. Check the troubleshooting section above
2. Review application logs in your deployment platform
3. Verify all environment variables are set correctly
4. Test locally first to isolate issues

