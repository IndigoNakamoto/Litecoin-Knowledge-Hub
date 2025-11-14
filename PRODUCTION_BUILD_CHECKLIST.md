# Production Build Checklist

This document verifies that all services are configured correctly for production builds.

## ✅ Verified Configurations

### Frontend (Next.js)
- [x] **Next.js Config**: `frontend/next.config.ts` has `output: 'standalone'` when `NODE_ENV=production`
- [x] **Dockerfile**: Sets `NODE_ENV=production` in builder stage before `npm run build`
- [x] **Dockerfile**: Uses multi-stage build with standalone output
- [x] **Dockerfile**: Build args for `NEXT_PUBLIC_BACKEND_URL` and `NEXT_PUBLIC_PAYLOAD_URL` are properly configured
- [x] **docker-compose.prod.yml**: Passes build args correctly

### Payload CMS (Next.js)
- [x] **Next.js Config**: `payload_cms/next.config.mjs` has `output: 'standalone'` when `NODE_ENV=production`
- [x] **Dockerfile**: Sets `NODE_ENV=production` in builder stage before `pnpm run build`
- [x] **Dockerfile**: Uses multi-stage build with standalone output
- [x] **Dockerfile**: Uses pnpm as package manager (matches package.json)

### Backend (FastAPI)
- [x] **Dockerfile**: Properly configured with Python 3.11-slim
- [x] **Dockerfile**: Installs dependencies from requirements.txt
- [x] **Dockerfile**: Sets PYTHONPATH correctly
- [x] **Dockerfile**: Has health check configured
- [x] **Dockerfile**: Runs uvicorn with correct module path (`backend.main:app`)

### Docker Compose
- [x] **docker-compose.prod.yml**: All services configured
- [x] **docker-compose.prod.yml**: Health checks configured
- [x] **docker-compose.prod.yml**: Service dependencies configured
- [x] **docker-compose.prod.yml**: Environment variables configured
- [x] **docker-compose.prod.yml**: Build args for frontend configured

## 🔧 Changes Made

### Frontend Dockerfile
- **Fixed**: Added `ENV NODE_ENV=production` in builder stage before build step
- **Purpose**: Ensures Next.js generates standalone output during Docker builds

### Payload CMS Dockerfile
- **Fixed**: Added `ENV NODE_ENV=production` in builder stage before build step
- **Purpose**: Ensures Next.js generates standalone output during Docker builds

## 📋 Build Process

### Frontend Build Process
1. **Dependencies Stage**: Installs npm dependencies
2. **Builder Stage**: 
   - Sets `NODE_ENV=production`
   - Sets `NEXT_PUBLIC_*` environment variables from build args
   - Runs `npm run build` which generates standalone output
3. **Runner Stage**: Copies standalone build and static files

### Payload CMS Build Process
1. **Dependencies Stage**: Installs pnpm and dependencies
2. **Builder Stage**:
   - Sets `NODE_ENV=production`
   - Runs `pnpm run build` which generates standalone output
3. **Runner Stage**: Copies standalone build and static files

### Backend Build Process
1. Installs system dependencies
2. Installs Python dependencies from requirements.txt
3. Copies application code
4. Sets PYTHONPATH
5. Exposes port 8000

## 🚀 Testing Production Builds

### Verify Configuration
```bash
./verify-production-builds.sh
```

### Test Docker Builds
```bash
# Build all services
docker-compose -f docker-compose.prod.yml build

# Build individual services
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml build frontend
docker-compose -f docker-compose.prod.yml build payload_cms
```

### Test Production Deployment
```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

## ⚠️ Required Environment Variables

### Backend
- `GOOGLE_API_KEY` - Required for embeddings and LLM
- `MONGO_URI` - MongoDB connection string
- `MONGO_DB_NAME` - Database name (default: `litecoin_rag_db`)
- `CORS_ORIGINS` - Allowed CORS origins

### Frontend
- `NEXT_PUBLIC_BACKEND_URL` - Backend API URL (passed as build arg)
- `NEXT_PUBLIC_PAYLOAD_URL` - Payload CMS URL (passed as build arg)

### Payload CMS
- `DATABASE_URI` - MongoDB connection string
- `PAYLOAD_SECRET` - Secure random secret
- `PAYLOAD_PUBLIC_SERVER_URL` - CMS server URL
- `BACKEND_URL` - Backend API URL

## 📝 Notes

1. **Standalone Output**: Both Next.js applications use standalone output mode, which includes only the necessary files for production, reducing image size.

2. **Build Args**: Frontend build args (`NEXT_PUBLIC_*`) must be set at build time, not runtime, as they are embedded in the Next.js build.

3. **NODE_ENV**: Setting `NODE_ENV=production` in the builder stage ensures Next.js configs enable standalone output and optimize the build.

4. **Health Checks**: All services have health checks configured in docker-compose.prod.yml.

5. **Service Dependencies**: Services are configured with proper dependency order (frontend depends on backend, etc.).

## 🔍 Verification Script

The `verify-production-builds.sh` script checks:
- Docker and docker-compose installation
- Environment files existence
- Next.js config standalone output
- Dockerfile NODE_ENV settings
- Dockerfile existence and configuration
- docker-compose.prod.yml configuration

Run it with:
```bash
./verify-production-builds.sh
```

