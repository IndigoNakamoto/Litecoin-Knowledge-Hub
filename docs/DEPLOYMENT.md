# Deployment Guide

This guide covers deploying all components of the Litecoin Knowledge Hub. The production stack consists of 9 services:

1. **Frontend** (Next.js) - User-facing chat interface
2. **Backend** (FastAPI) - RAG pipeline and API
3. **Payload CMS** (Next.js) - Content management system
4. **Admin Frontend** (Next.js) - System administration dashboard
5. **MongoDB** - Document database and vector store
6. **Redis** - Caching and rate limiting
7. **Prometheus** - Metrics collection
8. **Grafana** - Metrics visualization
9. **Cloudflared** (Optional) - Cloudflare tunnel for secure access

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Frontend Deployment (Next.js)](#frontend-deployment-nextjs)
- [Backend Deployment (FastAPI)](#backend-deployment-fastapi)
- [Payload CMS Deployment](#payload-cms-deployment)
- [Docker Deployment (All Services)](#docker-deployment-all-services)
- [Local RAG Deployment (Optional)](#local-rag-deployment-optional)
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

The project uses a **centralized environment variable management system**. For complete documentation of all environment variables, see [docs/setup/ENVIRONMENT_VARIABLES.md](./setup/ENVIRONMENT_VARIABLES.md).

### Quick Overview

Environment variables are organized into two categories:

1. **Root-level `.env.*` files** - Shared configuration (service URLs, database connections, monitoring)
   - `.env.docker.prod` - Production Docker deployment configuration
   - `.env.local` - Local development configuration
   - `.env.docker.dev` - Docker development configuration

2. **Service-specific `.env` files** - Secrets only (never committed to git)
   - `backend/.env` - Backend secrets (GOOGLE_API_KEY, WEBHOOK_SECRET, ADMIN_TOKEN)
   - `payload_cms/.env` - Payload CMS secrets (PAYLOAD_SECRET, WEBHOOK_SECRET)

### Docker Production Setup

For Docker production deployment, you need:

1. **Create `.env.docker.prod`** in the project root:
   ```bash
   cp .env.example .env.docker.prod
   ```

2. **Generate secure passwords** and add to `.env.docker.prod`:
   ```bash
   # Generate passwords
   MONGO_ROOT_PASSWORD=$(openssl rand -base64 32)
   MONGO_APP_PASSWORD=$(openssl rand -base64 32)
   REDIS_PASSWORD=$(openssl rand -base64 32)
   GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 32)
   
   # Add to .env.docker.prod
   echo "MONGO_ROOT_PASSWORD=$MONGO_ROOT_PASSWORD" >> .env.docker.prod
   echo "MONGO_APP_PASSWORD=$MONGO_APP_PASSWORD" >> .env.docker.prod
   echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> .env.docker.prod
   echo "GRAFANA_ADMIN_PASSWORD=$GRAFANA_ADMIN_PASSWORD" >> .env.docker.prod
   ```

3. **Update production URLs** in `.env.docker.prod`:
   - `PAYLOAD_PUBLIC_SERVER_URL=https://cms.lite.space`
   - `FRONTEND_URL=https://chat.lite.space`
   - `NEXT_PUBLIC_BACKEND_URL=https://api.lite.space`
   - `NEXT_PUBLIC_PAYLOAD_URL=https://cms.lite.space`
   - `CORS_ORIGINS=https://chat.lite.space,https://www.chat.lite.space`

4. **Update connection strings** with authentication in `.env.docker.prod`:
   - `MONGO_URI=mongodb://litecoin_app:${MONGO_APP_PASSWORD}@mongodb:27017/litecoin_rag_db?authSource=litecoin_rag_db`
   - `DATABASE_URI=mongodb://litecoin_app:${MONGO_APP_PASSWORD}@mongodb:27017/payload_cms?authSource=payload_cms`
   - `REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0`

5. **Create service-specific `.env` files**:
   ```bash
   # Generate shared webhook secret
   WEBHOOK_SECRET=$(openssl rand -base64 32)
   ADMIN_TOKEN=$(openssl rand -base64 32)
   
   # Backend secrets
   echo "GOOGLE_API_KEY=your-google-api-key-here" > backend/.env
   echo "WEBHOOK_SECRET=$WEBHOOK_SECRET" >> backend/.env
   echo "ADMIN_TOKEN=$ADMIN_TOKEN" >> backend/.env
   
   # Payload CMS secrets
   echo "PAYLOAD_SECRET=$(openssl rand -base64 32)" > payload_cms/.env
   echo "WEBHOOK_SECRET=$WEBHOOK_SECRET" >> payload_cms/.env
   ```

6. **Optional: Cloudflare Tunnel** - If using Cloudflare for secure access:
   ```bash
   echo "CLOUDFLARE_TUNNEL_TOKEN=your-tunnel-token" >> .env.docker.prod
   ```

**Important Notes:**
- MongoDB and Redis authentication is **required for production**
- `WEBHOOK_SECRET` must be identical in both `backend/.env` and `payload_cms/.env`
- See [Environment Variables Documentation](./setup/ENVIRONMENT_VARIABLES.md) for complete variable reference

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

The project includes a complete production Docker Compose configuration with all 9 services. The `docker-compose.prod.yml` file is already present in the project root.

### Prerequisites

Before deploying with Docker Compose, ensure you have:

1. **Environment variables configured** - See [Environment Variables](#environment-variables) section above
2. **Docker and Docker Compose installed**
3. **MongoDB users created** (if using authentication) - See [MongoDB/Redis Authentication Migration Guide](./setup/MONGODB_REDIS_AUTH_MIGRATION.md)

### Services Overview

The production stack includes:

1. **mongodb** - MongoDB 7.0 database with optional authentication
2. **backend** - FastAPI backend service (port 8000)
3. **payload_cms** - Payload CMS content management (port 3001)
4. **frontend** - Next.js user interface (port 3000)
5. **admin_frontend** - Next.js admin dashboard (port 3003)
6. **prometheus** - Metrics collection (port 9090, localhost only)
7. **grafana** - Metrics visualization (port 3002, localhost only)
8. **redis** - Caching and rate limiting
9. **cloudflared** - Cloudflare tunnel (optional)

### Deployment Steps

1. **Prepare environment files:**
   ```bash
   # Ensure .env.docker.prod exists (see Environment Variables section)
   # Ensure service-specific .env files exist:
   # - backend/.env (GOOGLE_API_KEY, WEBHOOK_SECRET, ADMIN_TOKEN)
   # - payload_cms/.env (PAYLOAD_SECRET, WEBHOOK_SECRET)
   ```

2. **Create MongoDB users** (required if using authentication):
   ```bash
   # See docs/setup/MONGODB_REDIS_AUTH_MIGRATION.md for instructions
   ```

3. **Deploy all services:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify services are running:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   ```

5. **View logs:**
   ```bash
   # All services
   docker-compose -f docker-compose.prod.yml logs -f
   
   # Specific service
   docker-compose -f docker-compose.prod.yml logs -f backend
   ```

### Service Details

#### MongoDB

- **Image:** `mongo:7.0`
- **Port:** Internal only (accessible via Docker network)
- **Authentication:** Optional (enabled if `MONGO_ROOT_PASSWORD` is set)
- **Health Check:** Checks MongoDB connectivity
- **Volume:** `mongodb_dev_data:/data/db` (persistent storage)

#### Backend

- **Build:** From `./backend/Dockerfile`
- **Port:** `8000:8000`
- **Health Check:** HTTP GET `/` endpoint
- **Dependencies:** Waits for MongoDB and Payload CMS to be healthy
- **Volumes:** Monitoring data persisted to `./backend/monitoring/data`

#### Payload CMS

- **Build:** From `./payload_cms/Dockerfile`
- **Port:** `3001:3000`
- **Health Check:** HTTP GET on port 3000
- **Dependencies:** Waits for MongoDB to be healthy

#### Frontend

- **Build:** From `./frontend/Dockerfile`
- **Port:** `3000:3000`
- **Build Args:** 
  - `NEXT_PUBLIC_BACKEND_URL` (default: `https://api.lite.space`)
  - `NEXT_PUBLIC_PAYLOAD_URL` (default: `https://cms.lite.space`)
- **Health Check:** HTTP GET on port 3000
- **Dependencies:** Waits for backend to be healthy

#### Admin Frontend

- **Build:** From `./admin-frontend/Dockerfile`
- **Port:** `3003:3000`
- **Build Args:** `NEXT_PUBLIC_BACKEND_URL`
- **Health Check:** HTTP GET on port 3000
- **Dependencies:** Waits for backend to be healthy
- **Note:** Typically runs locally; backend automatically adds admin frontend URL to CORS origins

#### Prometheus

- **Image:** `prom/prometheus:latest`
- **Port:** `127.0.0.1:9090:9090` (localhost only for security)
- **Volumes:**
  - `./monitoring/prometheus.yml` - Configuration
  - `./monitoring/alerts.yml` - Alert rules
  - `prometheus_data:/prometheus` - Metrics storage (30-day retention)
- **Dependencies:** Waits for backend to start

#### Grafana

- **Image:** `grafana/grafana:latest`
- **Port:** `127.0.0.1:3002:3000` (localhost only for security)
- **Credentials:** Set via `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD`
- **Volumes:**
  - `grafana_data:/var/lib/grafana` - Dashboard storage
  - `./monitoring/grafana/provisioning` - Auto-provisioned datasources
  - `./monitoring/grafana/dashboards` - Dashboard definitions
- **Dependencies:** Waits for Prometheus to start

#### Redis

- **Image:** `redis:7-alpine`
- **Port:** Internal only (accessible via Docker network)
- **Authentication:** Optional (enabled if `REDIS_PASSWORD` is set)
- **Persistence:** Saves every 60 seconds if at least 1 key changed
- **Volume:** `redis_data:/data` (persistent storage)

#### Cloudflared (Optional)

- **Image:** `cloudflare/cloudflared:latest`
- **Configuration:** Requires `CLOUDFLARE_TUNNEL_TOKEN` in `.env.docker.prod`
- **Purpose:** Provides secure tunnel to Cloudflare edge network
- **Dependencies:** Waits for backend and Payload CMS to be healthy

### Accessing Services

After deployment, services are accessible at:

- **Frontend:** `http://localhost:3000` (or your production domain)
- **Backend API:** `http://localhost:8000`
- **Payload CMS Admin:** `http://localhost:3001/admin`
- **Admin Frontend:** `http://localhost:3003` (if running locally)
- **Prometheus:** `http://localhost:9090` (localhost only)
- **Grafana:** `http://localhost:3002` (localhost only)

**Security Note:** Prometheus and Grafana are bound to localhost only for security. Use SSH port forwarding or a reverse proxy to access them remotely if needed.

### Monitoring Setup

The monitoring stack (Prometheus + Grafana) is automatically configured with:

- Pre-configured Prometheus datasource in Grafana
- Litecoin Knowledge Hub dashboard
- Alert rules for error rates, response times, LLM costs, and cache hit rates

See [Monitoring Documentation](../monitoring/README.md) for detailed information.

### Stopping Services

```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose -f docker-compose.prod.yml down -v
```

---

## Local RAG Deployment (Optional)

The system supports high-performance local RAG with cloud spillover, using local models for query rewriting, embeddings, and caching. This feature is **optional** and can be enabled via the `--local-rag` flag when starting the production stack.

### Overview

Local RAG services include:

1. **Ollama** - Local LLM for query rewriting (recommended: native on macOS for Metal acceleration)
2. **Infinity Embeddings** - Local embedding server for document embeddings (BGE-M3 model)
3. **Redis Stack** - Vector cache for semantic caching with HNSW index

### Prerequisites

1. **macOS with Apple Silicon (M1/M2/M3/M4)** - Recommended for native Metal (MPS) acceleration
   - For x86_64 systems, services will run in Docker with CPU acceleration
2. **Python 3.9+** - For native embedding server
3. **Ollama installed** - Download from [ollama.ai](https://ollama.ai) (for native deployment)

### Quick Start

**Option 1: Using the helper script (Recommended)**

```bash
# Start all services including local RAG
./scripts/run-prod.sh --local-rag

# Stop all services including local RAG
./scripts/down-prod.sh
```

**Option 2: Manual deployment**

```bash
# 1. Start local RAG services (Redis Stack, Ollama, Embedding Server)
./scripts/run-local-rag.sh

# 2. Start main production stack
docker-compose -f docker-compose.prod.yml up -d

# 3. Stop local RAG services
./scripts/down-local-rag.sh
```

### Configuration

#### 1. Environment Variables

Add to `.env.docker.prod`:

```bash
# Local RAG Configuration
USE_LOCAL_REWRITER=true          # Enable local query rewriting with Ollama
USE_INFINITY_EMBEDDINGS=true     # Enable local embeddings with Infinity
USE_REDIS_CACHE=true             # Enable semantic caching with Redis Stack

# Embedding Model (CRITICAL: Must be BAAI/bge-m3 for best quality)
EMBEDDING_MODEL_ID=BAAI/bge-m3   # Recommended: BGE-M3 (1024-dim, better Q&A)
# EMBEDDING_MODEL_ID=dunzhang/stella_en_1.5B_v5  # Legacy: Stella 1.5B (not recommended)

# Service URLs
OLLAMA_URL=http://host.docker.internal:11434              # Native Ollama on macOS
INFINITY_URL=http://host.docker.internal:7997             # Native embedding server on macOS
REDIS_STACK_URL=redis://redis_stack:6380                  # Docker Redis Stack

# Router Configuration
MAX_LOCAL_QUEUE_DEPTH=3           # Max queue depth before spillover to cloud
LOCAL_TIMEOUT_SECONDS=5.0         # Timeout for local services (seconds)

# Model Configuration
LOCAL_REWRITER_MODEL=llama3.2:3b  # Ollama model for query rewriting
VECTOR_DIMENSION=1024              # BGE-M3 vector dimension

# Redis Stack Cache Configuration
REDIS_CACHE_INDEX_NAME=cache:index
REDIS_CACHE_SIMILARITY_THRESHOLD=0.90
```

**⚠️ Important**: 
- Default `EMBEDDING_MODEL_ID` in code is `BAAI/bge-m3`, but `.env.docker.prod` may override it
- Always verify your `.env.docker.prod` has `EMBEDDING_MODEL_ID=BAAI/bge-m3` for optimal retrieval quality
- See [Embedding Model Update Guide](./fixes/EMBEDDING_MODEL_UPDATE.md) for migration instructions

#### 2. Native Ollama Setup (macOS)

For best performance on Apple Silicon, run Ollama natively:

```bash
# Install Ollama (if not already installed)
# Download from https://ollama.ai or:
brew install ollama

# Start Ollama service
ollama serve

# Pull the model (first time only)
ollama pull llama3.2:3b

# Verify it's running
curl http://localhost:11434/api/tags
```

The `run-local-rag.sh` script will detect native Ollama and skip starting the Dockerized version.

#### 3. Native Embedding Server Setup (macOS)

For Apple Silicon with Metal acceleration:

```bash
# Create virtual environment (if not already done)
python3 -m venv ~/infinity-env
source ~/infinity-env/bin/activate

# Install dependencies
pip install "sentence-transformers[torch]" fastapi uvicorn scikit-learn

# Start embedding server
source ~/infinity-env/bin/activate
export EMBEDDING_MODEL_ID='BAAI/bge-m3'
python scripts/local-rag/embeddings_server.py --device mps --port 7997 &

# Verify it's running
curl http://localhost:7997/health
```

**Note**: First run will download BGE-M3 model (~1.2GB). This is a one-time download.

#### 4. Redis Stack Setup

Redis Stack is started automatically via Docker Compose when using the `--local-rag` flag. It runs as part of the `local-rag` profile:

```bash
# Verify Redis Stack is running
docker ps | grep redis_stack

# Check Redis Stack logs
docker logs litecoin-redis-stack
```

### Services Architecture

```
┌─────────────────┐
│   Frontend      │
└────────┬────────┘
         │
┌────────▼────────┐
│    Backend      │
│  (FastAPI)      │
└────────┬────────┘
         │
    ┌────┴──────────────────┐
    │                       │
┌───▼────────┐      ┌───────▼──────────┐
│  Ollama    │      │ Infinity Server  │
│ (Native)   │      │   (Native MPS)   │
└────────────┘      └──────────────────┘
    │                       │
    └───────────┬───────────┘
                │
        ┌───────▼────────┐
        │  Redis Stack   │
        │  (Docker)      │
        └────────────────┘
```

### Feature Flags

Enable/disable individual components via environment variables:

- `USE_LOCAL_REWRITER=true` - Use Ollama for query rewriting (spills to Gemini if timeout/queue full)
- `USE_INFINITY_EMBEDDINGS=true` - Use local Infinity server for embeddings (1024-dim BGE-M3)
- `USE_REDIS_CACHE=true` - Use Redis Stack for semantic caching (HNSW vector index)

All flags default to `false` - enable them explicitly in `.env.docker.prod`.

### Vector Store Re-indexing

After enabling local RAG, you may need to re-index documents with the new embedding model:

```bash
# Set environment variables
export INFINITY_URL=http://localhost:7997
export MONGO_URI="your-mongodb-uri"
export EMBEDDING_MODEL_ID=BAAI/bge-m3

# Activate virtual environment
source ~/infinity-env/bin/activate

# Install re-indexing dependencies
pip install pymongo faiss-cpu langchain langchain-community

# Run re-indexing script
python scripts/reindex_vectors.py
```

The script will:
1. Fetch all documents from MongoDB
2. Generate 1024-dim embeddings using BGE-M3
3. Create FAISS index at `backend/faiss_index_1024/`
4. Update `FAISS_INDEX_PATH_1024` in `.env.docker.prod`

### Verification

1. **Check Ollama**:
   ```bash
   curl http://localhost:11434/api/tags
   # Should return: {"models":[...]}
   ```

2. **Check Embedding Server**:
   ```bash
   curl http://localhost:7997/health
   # Should return: {"status":"healthy","model":"BAAI/bge-m3"}
   ```

3. **Check Redis Stack**:
   ```bash
   docker exec -it litecoin-redis-stack redis-cli -p 6380 PING
   # Should return: PONG
   ```

4. **Check Backend Logs**:
   ```bash
   docker logs litecoin-backend | grep -E "(InfinityEmbeddings|InferenceRouter|RedisVectorCache)"
   # Should show initialization messages
   ```

5. **Test RAG Query**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/stream \
     -H "Content-Type: application/json" \
     -d '{"query": "What is Litecoin?", "chat_history": []}'
   ```

### Performance Tuning

1. **Memory Optimization** (see [Memory Optimization Guide](./fixes/MEMORY_OPTIMIZATION.md)):
   - Reduce Docker Desktop VM memory to 8GB
   - Use `float16` for BGE-M3 on MPS (already enabled)
   - Set backend container memory limit: `deploy.resources.limits.memory: 2G`

2. **Query Rewriting Timeout**:
   - Increase `LOCAL_TIMEOUT_SECONDS` if Ollama is slow (default: 5.0s)
   - System automatically spills to Gemini if timeout exceeded

3. **Retrieval Quality**:
   - Ensure `EMBEDDING_MODEL_ID=BAAI/bge-m3` (not Stella 1.5B)
   - Adjust `VECTOR_SEARCH_SIMILARITY_THRESHOLD` (default: 0.75) to filter irrelevant documents
   - Increase `RETRIEVER_K` (default: 12) for more context

### Troubleshooting

**Issue: Embedding server not starting**
- Check Python version: `python3 --version` (needs 3.9+)
- Verify virtual environment is activated
- Check logs: `tail -f logs/embeddings_server.log`

**Issue: Backend can't connect to embedding server**
- Verify `INFINITY_URL=http://host.docker.internal:7997` in `.env.docker.prod`
- Check embedding server is running: `curl http://localhost:7997/health`
- Restart backend: `docker restart litecoin-backend`

**Issue: Poor retrieval quality**
- Verify `EMBEDDING_MODEL_ID=BAAI/bge-m3` in `.env.docker.prod`
- Re-index documents with BGE-M3 (see Vector Store Re-indexing above)
- Check similarity threshold: `VECTOR_SEARCH_SIMILARITY_THRESHOLD=0.75`

**Issue: Ollama timeout errors**
- Increase `LOCAL_TIMEOUT_SECONDS` in `.env.docker.prod`
- Check Ollama is responding: `curl http://localhost:11434/api/tags`
- Consider using native Ollama instead of Dockerized version

**Issue: Memory pressure spikes**
- Reduce Docker Desktop VM memory to 8GB
- Verify backend container has memory limit: `deploy.resources.limits.memory: 2G`
- See [Memory Optimization Guide](./fixes/MEMORY_OPTIMIZATION.md)

### Related Documentation

- [High-Performance Local RAG Feature](./features/DEC6_FEATURE_HIGH_PERFORMANCE_LOCAL_RAG.md) - Complete feature documentation
- [Embedding Model Update Guide](./fixes/EMBEDDING_MODEL_UPDATE.md) - Migrating from Stella to BGE-M3
- [Memory Optimization Guide](./fixes/MEMORY_OPTIMIZATION.md) - Reducing memory usage
- [UnboundLocalError Fix](./fixes/UNBOUNDLOCALERROR_FIX.md) - Bug fix documentation

---

## Post-Deployment Checklist

After deploying all services, verify the following:

### 1. Service Health Checks

Check that all services are running:
```bash
docker-compose -f docker-compose.prod.yml ps
```

All services should show "Up" status.

### 2. Backend Health Check

```bash
# Local access
curl http://localhost:8000/

# Or via production domain
curl https://your-backend-domain.com/

# Should return: {"Hello": "World"}
```

### 3. Frontend Accessibility
- Visit your frontend URL (`http://localhost:3000` or production domain)
- Verify the UI loads correctly
- Test API connectivity by submitting a query

### 4. Payload CMS Admin Panel
- Visit `http://localhost:3001/admin` (or production CMS URL)
- Login with admin credentials
- Verify content collections are accessible
- Check that articles are visible

### 5. Admin Frontend (if running locally)
- Visit `http://localhost:3003`
- Verify connection to backend
- Test system management features

### 6. Webhook Synchronization
- Create a test article in Payload CMS
- Publish it
- Verify it syncs to the backend (check `/api/v1/sources`)
- Query the RAG pipeline to confirm the article is indexed

### 7. RAG Pipeline Test
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Litecoin?",
    "chat_history": []
  }'
```

### 8. CORS Configuration
- Verify frontend can make requests to backend
- Check browser console for CORS errors
- If running admin frontend locally, verify it can connect to backend

### 9. MongoDB Connection
```bash
# Check MongoDB logs
docker-compose -f docker-compose.prod.yml logs mongodb

# Verify authentication is working (if enabled)
docker exec -it litecoin-mongodb mongosh -u litecoin_app -p
```

### 10. Redis Connection
```bash
# Check Redis logs
docker-compose -f docker-compose.prod.yml logs redis

# Test Redis connectivity (if password is not set)
docker exec -it litecoin-redis redis-cli ping

# Test Redis connectivity (if password is set)
docker exec -it litecoin-redis redis-cli -a $REDIS_PASSWORD ping
```

### 11. Prometheus Metrics
- Visit `http://localhost:9090`
- Check that backend target is UP (Status → Targets)
- Try a query: `rate(http_requests_total[5m])`

### 12. Grafana Dashboard
- Visit `http://localhost:3002`
- Login with admin credentials (set via `GRAFANA_ADMIN_PASSWORD`)
- Navigate to Dashboards → Litecoin Knowledge Hub - Monitoring Dashboard
- Verify metrics are being collected

### 13. Environment Variables
- Verify all environment variables are set correctly in `.env.docker.prod`
- Check that service-specific `.env` files exist and contain required secrets
- Verify sensitive data (API keys, secrets) are not exposed in logs or environment

### 14. Logs Review
```bash
# Check for errors across all services
docker-compose -f docker-compose.prod.yml logs | grep -i error

# Check specific service logs
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend
```

### 15. Cloudflare Tunnel (if enabled)
- Verify tunnel is running: `docker-compose -f docker-compose.prod.yml logs cloudflared`
- Check Cloudflare dashboard for tunnel status
- Verify routes are configured correctly

---

## Troubleshooting

### Docker Compose Issues

**Issue: Services fail to start**
```bash
# Check service logs
docker-compose -f docker-compose.prod.yml logs [service-name]

# Check if ports are already in use
netstat -tulpn | grep :8000
netstat -tulpn | grep :3000

# Verify environment files exist
ls -la .env.docker.prod backend/.env payload_cms/.env
```

**Issue: Health checks failing**
- Check service logs for startup errors
- Verify dependencies (MongoDB, Redis) are healthy
- Increase `start_period` in healthcheck if services need more time to start

### Backend Issues

**Issue: MongoDB connection fails**
- Verify `MONGO_URI` in `.env.docker.prod` is correct
- Check MongoDB container is running: `docker ps | grep mongodb`
- Verify authentication credentials if authentication is enabled
- Check MongoDB logs: `docker-compose -f docker-compose.prod.yml logs mongodb`
- Ensure MongoDB users are created (see [MongoDB/Redis Authentication Migration Guide](./setup/MONGODB_REDIS_AUTH_MIGRATION.md))

**Issue: Redis connection fails**
- Verify `REDIS_URL` in `.env.docker.prod` is correct
- Check Redis container is running: `docker ps | grep redis`
- Verify password is set correctly if authentication is enabled
- Check Redis logs: `docker-compose -f docker-compose.prod.yml logs redis`

**Issue: CORS errors**
- Verify `CORS_ORIGINS` in `.env.docker.prod` includes your frontend URL
- If running admin frontend locally, set `ADMIN_FRONTEND_URL` or add to `CORS_ORIGINS`
- Check backend logs for CORS rejection messages

**Issue: FAISS index not found**
- In production with MongoDB Atlas Vector Search, FAISS is not needed
- The system automatically uses MongoDB Atlas for vector search in production
- Remove `FAISS_INDEX_PATH` from environment variables if present

### Frontend Issues

**Issue: API requests fail**
- Verify `NEXT_PUBLIC_BACKEND_URL` is set correctly (build-time variable)
- Rebuild frontend image after changing `NEXT_PUBLIC_*` variables
- Check `next.config.ts` rewrites configuration
- Verify backend CORS allows frontend origin
- Check browser console for specific error messages

**Issue: Build fails**
- Verify Node.js version compatibility
- Check build logs: `docker-compose -f docker-compose.prod.yml build frontend`
- Ensure all dependencies are listed in `package.json`

### Payload CMS Issues

**Issue: Cannot connect to database**
- Verify `DATABASE_URI` in `.env.docker.prod` is correct
- Check MongoDB container is accessible from Payload CMS container
- Verify authentication credentials if authentication is enabled
- Check Payload CMS logs: `docker-compose -f docker-compose.prod.yml logs payload_cms`

**Issue: Webhooks not syncing**
- Verify `BACKEND_URL` in `.env.docker.prod` points to backend service
- Verify `WEBHOOK_SECRET` is identical in both `backend/.env` and `payload_cms/.env`
- Check backend `/api/v1/sync/payload` endpoint is accessible
- Review Payload CMS webhook logs in admin panel
- Check backend logs for webhook processing errors

### Monitoring Issues

**Issue: Prometheus not scraping metrics**
- Verify backend is healthy: `curl http://localhost:8000/health`
- Check Prometheus targets: `http://localhost:9090/targets`
- Verify `prometheus.yml` configuration
- Check Prometheus logs: `docker-compose -f docker-compose.prod.yml logs prometheus`

**Issue: Grafana cannot connect to Prometheus**
- Verify Prometheus is running: `docker ps | grep prometheus`
- Check Grafana datasource configuration
- Verify Prometheus URL is correct (`http://prometheus:9090` in Docker network)
- Check Grafana logs: `docker-compose -f docker-compose.prod.yml logs grafana`

### Cloudflare Tunnel Issues

**Issue: Tunnel not connecting**
- Verify `CLOUDFLARE_TUNNEL_TOKEN` is set in `.env.docker.prod`
- Check tunnel token is valid in Cloudflare dashboard
- Review tunnel logs: `docker-compose -f docker-compose.prod.yml logs cloudflared`
- Verify routes are configured in Cloudflare dashboard

---

## Additional Resources

### Project Documentation

- [Environment Variables Documentation](./setup/ENVIRONMENT_VARIABLES.md) - Complete guide to all environment variables
- [MongoDB/Redis Authentication Migration Guide](./setup/MONGODB_REDIS_AUTH_MIGRATION.md) - Setting up authentication for production
- [Monitoring Documentation](../monitoring/README.md) - Prometheus and Grafana setup
- [Testing Documentation](../TESTING.md) - Running the test suite

### External Documentation

- [Vercel Deployment Docs](https://vercel.com/docs)
- [Railway Deployment Docs](https://docs.railway.app/)
- [Render Deployment Docs](https://render.com/docs)
- [Fly.io Deployment Docs](https://fly.io/docs/)
- [Payload CMS Deployment](https://payloadcms.com/docs/deployment/overview)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

---

## Support

For deployment issues, please:
1. Check the troubleshooting section above
2. Review application logs in your deployment platform
3. Verify all environment variables are set correctly
4. Test locally first to isolate issues

