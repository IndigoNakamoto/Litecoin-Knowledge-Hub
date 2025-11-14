# Docker Development Setup

This guide explains how to run the Litecoin Knowledge Hub in development mode using Docker with hot reload enabled for both backend and frontend.

## Prerequisites

- Docker and Docker Compose installed
- Environment variables configured (see [Environment Setup](#environment-setup))

## Quick Start

1. **Start all services:**
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

2. **View combined logs (backend + frontend):**
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f backend frontend
   ```

3. **Access the services:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Payload CMS: http://localhost:3001
   - MongoDB: localhost:27017

## Environment Setup

### Backend Environment Variables

Create or update `backend/.env` with the following variables:

```env
# MongoDB Connection
MONGO_URI=mongodb://mongodb:27017
MONGO_DB_NAME=litecoin_rag_db
MONGO_COLLECTION_NAME=litecoin_docs

# Google AI API Key (required for LLM)
GOOGLE_API_KEY=your-google-api-key-here

# Optional: Logging
LOG_LEVEL=INFO
JSON_LOGGING=false
```

### Frontend Environment Variables

The frontend uses environment variables set in `docker-compose.dev.yml`. These are automatically configured for development:
- `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000`
- `NEXT_PUBLIC_PAYLOAD_URL=http://localhost:3001`

### Payload CMS Environment Variables

Create or update `payload_cms/.env` with the following variables:

```env
# MongoDB Connection
DATABASE_URI=mongodb://mongodb:27017/payload_cms

# Payload Configuration
PAYLOAD_SECRET=your-secret-key-here
PAYLOAD_PUBLIC_SERVER_URL=http://localhost:3001
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://backend:8000
```

## Common Commands

### Starting Services

**Start all services in foreground:**
```bash
docker-compose -f docker-compose.dev.yml up
```

**Start all services in background:**
```bash
docker-compose -f docker-compose.dev.yml up -d
```

**Start specific services only:**
```bash
# Start only backend and MongoDB
docker-compose -f docker-compose.dev.yml up backend mongodb

# Start only frontend (requires backend to be running)
docker-compose -f docker-compose.dev.yml up frontend
```

### Viewing Logs

**View combined logs for backend and frontend:**
```bash
docker-compose -f docker-compose.dev.yml logs -f backend frontend
```

**View logs for a specific service:**
```bash
# Backend only
docker-compose -f docker-compose.dev.yml logs -f backend

# Frontend only
docker-compose -f docker-compose.dev.yml logs -f frontend

# Payload CMS only
docker-compose -f docker-compose.dev.yml logs -f payload_cms

# All services
docker-compose -f docker-compose.dev.yml logs -f
```

**View logs without following (show last 100 lines):**
```bash
docker-compose -f docker-compose.dev.yml logs --tail=100 backend frontend
```

### Stopping Services

**Stop all services:**
```bash
docker-compose -f docker-compose.dev.yml down
```

**Stop services and remove volumes (clean slate):**
```bash
docker-compose -f docker-compose.dev.yml down -v
```

**Stop services but keep containers:**
```bash
docker-compose -f docker-compose.dev.yml stop
```

### Rebuilding Services

**Rebuild and start services:**
```bash
docker-compose -f docker-compose.dev.yml up --build
```

**Rebuild specific service:**
```bash
docker-compose -f docker-compose.dev.yml build backend
docker-compose -f docker-compose.dev.yml up -d backend
```

## Hot Reload

Hot reload is enabled for all services:

- **Backend (FastAPI)**: Uses `uvicorn --reload` flag. Changes to Python files in `backend/` will automatically restart the server.
- **Frontend (Next.js)**: Uses `npm run dev`. Changes to files in `frontend/src/` will automatically trigger recompilation and browser refresh.
- **Payload CMS (Next.js)**: Uses `pnpm dev`. Changes to files in `payload_cms/src/` will automatically trigger recompilation.

### How It Works

- Code directories are mounted as volumes, allowing live editing
- `node_modules` and build artifacts (`.next`, `__pycache__`) are stored in named Docker volumes to avoid conflicts
- File watching is enabled with polling (`WATCHPACK_POLLING=true`) to ensure changes are detected in Docker

### Testing Hot Reload

1. **Backend**: Edit any Python file in `backend/` (e.g., `backend/main.py`) and save. You should see "Reloading..." in the backend logs.

2. **Frontend**: Edit any React component in `frontend/src/` (e.g., `frontend/src/app/page.tsx`) and save. The browser should automatically refresh.

3. **Payload CMS**: Edit any file in `payload_cms/src/` and save. The dev server will recompile.

## Service Communication

Services communicate using Docker's internal network:

- **Frontend → Backend**: `http://localhost:8000` (from browser) or `http://backend:8000` (from container)
- **Payload CMS → Backend**: `http://backend:8000`
- **Backend → MongoDB**: `mongodb://mongodb:27017`
- **Payload CMS → MongoDB**: `mongodb://mongodb:27017/payload_cms`

## Troubleshooting

### Services Won't Start

**Check if ports are already in use:**
```bash
# Check port 8000 (backend)
lsof -i :8000

# Check port 3000 (frontend)
lsof -i :3000

# Check port 3001 (payload_cms)
lsof -i :3001

# Check port 27017 (MongoDB)
lsof -i :27017
```

**View service status:**
```bash
docker-compose -f docker-compose.dev.yml ps
```

### Hot Reload Not Working

**For Backend:**
- Ensure you're editing files in `backend/` directory
- Check backend logs: `docker-compose -f docker-compose.dev.yml logs backend`
- Verify the volume mount is correct: `docker-compose -f docker-compose.dev.yml config`

**For Frontend/Next.js:**
- Ensure `WATCHPACK_POLLING=true` is set (already configured in docker-compose.dev.yml)
- Try restarting the service: `docker-compose -f docker-compose.dev.yml restart frontend`
- Check if `node_modules` volume is causing issues (try removing it): `docker volume rm litecoin-knowledge-hub_frontend_node_modules`

### MongoDB Connection Issues

**Check MongoDB is running:**
```bash
docker-compose -f docker-compose.dev.yml ps mongodb
```

**View MongoDB logs:**
```bash
docker-compose -f docker-compose.dev.yml logs mongodb
```

**Connect to MongoDB directly:**
```bash
docker-compose -f docker-compose.dev.yml exec mongodb mongosh
```

### Build Errors

**Clear Docker build cache:**
```bash
docker-compose -f docker-compose.dev.yml build --no-cache
```

**Remove all containers and volumes:**
```bash
docker-compose -f docker-compose.dev.yml down -v
docker system prune -a
```

### Environment Variables Not Loading

- Ensure `.env` files exist in `backend/` and `payload_cms/` directories
- Check environment variables are set correctly: `docker-compose -f docker-compose.dev.yml config`
- Restart services after changing environment variables: `docker-compose -f docker-compose.dev.yml restart`

### Frontend Can't Connect to Backend

- Verify backend is running: `docker-compose -f docker-compose.dev.yml ps backend`
- Check backend logs for errors: `docker-compose -f docker-compose.dev.yml logs backend`
- Verify CORS settings in backend allow `http://localhost:3000`
- Check browser console for CORS errors

### Payload CMS Issues

**First-time setup:**
- Access http://localhost:3001
- Create your first admin user
- Configure collections as needed

**Database connection:**
- Ensure MongoDB is running and healthy
- Check `DATABASE_URI` in `payload_cms/.env` is correct
- Verify Payload CMS can connect: `docker-compose -f docker-compose.dev.yml logs payload_cms`

## Development Workflow

1. **Start services:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **View logs in a separate terminal:**
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f backend frontend
   ```

3. **Make code changes** in your editor (files are mounted as volumes)

4. **Watch for hot reload** in the logs

5. **Test changes** in the browser (Frontend) or via API calls (Backend)

6. **Stop services when done:**
   ```bash
   docker-compose -f docker-compose.dev.yml down
   ```

## Differences from Production

The development setup differs from production in several ways:

- **Hot reload enabled**: Code changes trigger automatic recompilation
- **Volume mounts**: Local code is mounted into containers for live editing
- **Development mode**: Services run in development mode (no optimizations)
- **No monitoring**: Prometheus and Grafana are excluded
- **No tunnel**: Cloudflared tunnel is excluded
- **Separate MongoDB volume**: Uses `mongodb_dev_data` to avoid conflicts with production data
- **Different container names**: All containers have `-dev` suffix

## Additional Resources

- [Production Deployment Guide](./DEPLOYMENT.md)
- [Monitoring Setup](./monitoring/README.md)
- [Backend API Documentation](http://localhost:8000/docs) (when backend is running)
- [Payload CMS Admin Panel](http://localhost:3001/admin) (when Payload CMS is running)

