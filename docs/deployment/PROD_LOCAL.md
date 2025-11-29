# Local Production Build Verification Guide

## Overview

The production-local environment allows you to run production builds locally for verification and debugging. This uses the same production Dockerfiles and configuration as the production environment, but with localhost URLs for local access.

## Purpose

- **Verify production builds** work correctly before deployment
- **Debug production issues** in a local environment
- **Test production configurations** without affecting production

## Setup

### 1. Create `.env.prod-local` File

Copy the example file and customize as needed:

```bash
cp .env.example .env.prod-local
```

The `.env.example` file contains a comprehensive template with all available environment variables. At minimum, you need to set the URL configuration for localhost access:

```bash
# Backend URL - use localhost for local access
BACKEND_URL=http://localhost:8000

# Payload CMS URLs - use localhost for local access
PAYLOAD_PUBLIC_SERVER_URL=http://localhost:3001
FRONTEND_URL=http://localhost:3000

# Frontend public URLs - use localhost for local access
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_PAYLOAD_URL=http://localhost:3001

# CORS Origins - include localhost for local access
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

**Note:** The `.env.prod-local` file is gitignored and should not be committed. Each developer should create their own copy from `.env.example`.

### 2. Ensure Required Environment Variables

Make sure you have the necessary environment variables set in your service-specific `.env` files:
- `backend/.env` - Backend configuration (GOOGLE_API_KEY, MONGO_URI, etc.)
- `payload_cms/.env` - Payload CMS configuration (DATABASE_URI, PAYLOAD_SECRET, etc.)

⚠️ **Note:** Currently, MongoDB and Redis run without authentication. When authentication is enabled (required for public launch - see [RED_TEAM_ASSESSMENT_COMBINED.md](./RED_TEAM_ASSESSMENT_COMBINED.md)), connection strings will need to include credentials.

## Usage

### Option 1: Using the Helper Script (Recommended)

```bash
./scripts/run-prod-local.sh
```

This script will:
1. Check if `.env.prod-local` exists
2. Check for existing containers that might conflict (and warn you)
3. Load environment variables from `.env.prod-local`
4. Run `docker-compose.prod-local.yml` with production builds

**Note:** If you have existing containers from previous runs, the script will prompt you. You can stop them first with:
```bash
docker-compose -f docker-compose.prod-local.yml down
docker-compose -f docker-compose.dev.yml down
```

### Option 2: Manual Command

```bash
# Export variables from .env.prod-local
export $(cat .env.prod-local | xargs)

# Run docker-compose with production-local file
docker-compose -f docker-compose.prod-local.yml up --build
```

### Option 3: One-liner

```bash
export $(cat .env.prod-local | xargs) && docker-compose -f docker-compose.prod-local.yml up --build
```

## Services

The production-local environment includes the full production stack:

- **MongoDB** - Database (port 27017)
- **Backend** - FastAPI backend (port 8000)
- **Payload CMS** - Content management (port 3001)
- **Frontend** - Next.js frontend (port 3000)
- **Prometheus** - Metrics collection (port 9090)
- **Grafana** - Metrics visualization (port 3002)
- **Cloudflared** - Tunnel (optional, disabled if CLOUDFLARE_TUNNEL_TOKEN not set)

## Accessing Services

Once started, you can access:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend API Docs: http://localhost:8000/docs
- Payload CMS Admin: http://localhost:3001/admin
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3002 (requires GRAFANA_ADMIN_PASSWORD env var)

## Differences from Development

| Aspect | Development | Production-Local | Production |
|--------|------------|------------------|------------|
| Dockerfiles | `Dockerfile.dev` | `Dockerfile` (prod) | `Dockerfile` (prod) |
| Hot Reload | ✅ Yes | ❌ No | ❌ No |
| Code Mounts | ✅ Yes | ❌ No | ❌ No |
| Build Optimization | ❌ No | ✅ Yes | ✅ Yes |
| Monitoring | ❌ No | ✅ Yes | ✅ Yes |
| URLs | localhost | localhost | Production domains |
| NODE_ENV | development | production | production |
| Container Names | `-dev` suffix | `-prod-local` suffix | No suffix |

## Differences from Production

| Aspect | Production-Local | Production |
|--------|------------------|------------|
| URLs | localhost | Production domains |
| Cloudflared | Optional | Required |
| Container Names | `-prod-local` suffix | No suffix |
| Volumes | Separate | Separate |

## Troubleshooting

### Container Name Conflicts

If you get an error like "The container name is already in use", stop existing containers first:

```bash
# Stop any running docker-compose environments
docker-compose -f docker-compose.prod-local.yml down
docker-compose -f docker-compose.dev.yml down

# Or stop all litecoin containers
docker ps -a --filter "name=litecoin-" --format "{{.Names}}" | xargs -r docker stop
docker ps -a --filter "name=litecoin-" --format "{{.Names}}" | xargs -r docker rm
```

The `run-prod-local.sh` script will now warn you about existing containers and ask for confirmation before proceeding.

### Port Conflicts

If you get port conflicts, make sure:
- Development environment is stopped: `docker-compose -f docker-compose.dev.yml down`
- Production-local environment is stopped: `docker-compose -f docker-compose.prod-local.yml down`
- No other services are using ports 3000, 3001, 8000, 9090, 3002, 27017

### Environment Variables Not Loading

- Ensure `.env.prod-local` exists in the project root
- Check that `.env.prod-local` has no syntax errors
- Verify variables are exported: `env | grep BACKEND_URL`

### Build Failures

- Ensure all required environment variables are set in service `.env` files
- Check Docker build logs: `docker-compose -f docker-compose.prod-local.yml build --no-cache`
- Verify Dockerfile syntax and dependencies

### Service Not Starting

- Check service logs: `docker-compose -f docker-compose.prod-local.yml logs <service-name>`
- Verify health checks: `docker ps` (check STATUS column)
- Ensure MongoDB is healthy before other services start

## Security Considerations

⚠️ **IMPORTANT: MongoDB and Redis Authentication (Public Launch Blocker)**

The production-local environment uses the same Docker Compose configuration as production, which currently runs MongoDB and Redis without authentication. This is acceptable for local testing but **must be enabled before public launch** (see [RED_TEAM_ASSESSMENT_COMBINED.md](./RED_TEAM_ASSESSMENT_COMBINED.md) - CRIT-3, CRIT-4).

**When authentication is enabled:**
- Update `MONGO_URI` and `DATABASE_URI` to include credentials
- Update `REDIS_URL` to include password
- Test authentication flow in production-local before deploying

**Status:** Code already written, needs to be enabled (~1-2 hours). See security assessment for details.

## Best Practices

1. **Always test in production-local** before deploying to production
2. **Use production-local for debugging** production-like issues
3. **Keep `.env.prod-local` updated** with any new environment variables
4. **Clean up after testing**: `docker-compose -f docker-compose.prod-local.yml down -v`
5. **Don't commit `.env.prod-local`** - it's gitignored for a reason
6. **Enable MongoDB/Redis authentication** before public deployment

## Cleanup

To stop and remove all production-local containers and volumes:

```bash
docker-compose -f docker-compose.prod-local.yml down -v
```

To stop but keep volumes (faster for next run):

```bash
docker-compose -f docker-compose.prod-local.yml down
```


