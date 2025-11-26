# Docker Environment Switching Guide

## Overview

This project uses two Docker Compose configurations:
- **Development**: `docker-compose.dev.yml` - Hot reload, development tools
- **Production**: `docker-compose.prod.yml` - Optimized builds, monitoring, Cloudflare tunnel

## Key Differences

### Development (`docker-compose.dev.yml`)
- Uses `Dockerfile.dev` for frontend and payload_cms (simple, no build step)
- Code mounted as volumes for hot reload
- Separate volumes for `node_modules` and `.next` to avoid conflicts
- Development environment variables
- No healthchecks (faster startup)
- No monitoring services

### Production (`docker-compose.prod.yml`)
- Uses production `Dockerfile` with multi-stage builds
- Code baked into image (no volume mounts for code)
- Optimized standalone Next.js builds
- Production environment variables
- Healthchecks enabled
- Includes Prometheus, Grafana, and Cloudflare tunnel

## When to Rebuild

### Always Rebuild When:
1. **Switching from dev to prod** - Different Dockerfiles are used
2. **Dependencies change** - `package.json`, `requirements.txt`, etc.
3. **Dockerfile changes** - Any modifications to build process
4. **Environment variables change** - Build-time args (e.g., `NEXT_PUBLIC_*`)

### Rebuild Not Needed When:
1. **Only code changes** (dev mode) - Hot reload handles it
2. **Only runtime env vars change** - Restart containers instead
3. **Switching back to dev** - If you haven't changed dependencies

## Build Flags: When to Use `--no-cache`

### Use `--no-cache` When:
- ✅ **First time building** after cloning the repo
- ✅ **Dependency versions changed** (package.json, requirements.txt)
- ✅ **Build is failing mysteriously** - Cache might be corrupted
- ✅ **Switching between dev/prod** - Ensures clean build
- ✅ **Dockerfile changed** - Old cache might interfere
- ✅ **Before deploying to production** - Ensures reproducible builds

### Don't Use `--no-cache` When:
- ❌ **Regular development** - Slows down builds significantly
- ❌ **Only code changes** - Cache speeds up rebuilds
- ❌ **Quick iteration** - Use regular `docker-compose build`

## Recommended Workflow

### Switching from Dev to Prod

```bash
# 1. Stop dev environment
docker-compose -f docker-compose.dev.yml down

# 2. Clean build for production (recommended)
docker-compose -f docker-compose.prod.yml build --no-cache

# 3. Start production
docker-compose -f docker-compose.prod.yml up -d

# Or if you're confident cache is good:
docker-compose -f docker-compose.prod.yml up --build -d
```

### Switching from Prod to Dev

```bash
# 1. Stop production
docker-compose -f docker-compose.prod.yml down

# 2. Build dev (usually no --no-cache needed unless dependencies changed)
docker-compose -f docker-compose.dev.yml build

# 3. Start dev
docker-compose -f docker-compose.dev.yml up -d
```

### Quick Dev Iteration (No Rebuild)

```bash
# Just restart if only code changed
docker-compose -f docker-compose.dev.yml restart backend frontend payload_cms
```

## Environment Variables

### Important Considerations:

1. **Different env files**:
   - Dev: `.env.docker.dev`
   - Prod: `.env.docker.prod`

2. **Build-time vs Runtime**:
   - `NEXT_PUBLIC_*` variables are build-time (need rebuild)
   - Other env vars are runtime (just restart)

3. **Check before switching**:
   ```bash
   # Verify env files exist
   ls -la .env.docker.dev .env.docker.prod
   ```

## Volume Management

### Development Volumes
- `frontend_node_modules` - Prevents conflicts with host
- `frontend_next` - Next.js build cache
- `payload_cms_node_modules` - Prevents conflicts
- `payload_cms_next` - Next.js build cache
- `backend_pycache` - Python cache

### Production Volumes
- `prometheus_data` - Metrics storage
- `grafana_data` - Dashboard data
- `mongodb_dev_data` - Database (⚠️ shared with dev!)
- `redis_data` - Cache storage

⚠️ **Warning**: Both dev and prod use `mongodb_dev_data` volume. Consider using separate volumes for production data.

## Cleanup Commands

### Remove All Containers and Networks
```bash
# Dev
docker-compose -f docker-compose.dev.yml down -v

# Prod
docker-compose -f docker-compose.prod.yml down -v
```

### Remove Only Unused Volumes
```bash
docker volume prune
```

### Full Cleanup (Nuclear Option)
```bash
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.prod.yml down -v
docker system prune -a --volumes
```

## Troubleshooting

### Issue: "Container name already in use"
**Solution**: Stop the other environment first
```bash
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.prod.yml down
```

### Issue: "Port already in use"
**Solution**: Check what's using the port
```bash
lsof -i :8000  # Backend
lsof -i :3000  # Frontend
lsof -i :3001  # Payload CMS
```

### Issue: "Build cache issues"
**Solution**: Clean build
```bash
docker-compose -f docker-compose.prod.yml build --no-cache
```

### Issue: "Environment variables not working"
**Solution**: 
1. Check env files exist
2. Rebuild if `NEXT_PUBLIC_*` vars changed
3. Restart containers for runtime vars

## Security Considerations

⚠️ **IMPORTANT: MongoDB and Redis Authentication (Public Launch Blocker)**

Currently, MongoDB and Redis run without authentication in Docker Compose configurations. This is acceptable for local-only development but **must be enabled before public launch** (see [RED_TEAM_ASSESSMENT_COMBINED.md](./RED_TEAM_ASSESSMENT_COMBINED.md) - CRIT-3, CRIT-4).

**When authentication is enabled:**
- MongoDB connection strings will need to include credentials: `mongodb://username:password@mongodb:27017/...`
- Redis connection strings will need to include password: `redis://:password@redis:6379/0`
- Update all `MONGO_URI`, `DATABASE_URI`, and `REDIS_URL` environment variables
- Update Docker Compose files to configure authentication
- Test authentication flow after enabling

**Status:** Code already written, needs to be enabled (~1-2 hours). See security assessment for details.

## Best Practices

1. **Always stop one environment before starting the other**
2. **Use `--no-cache` for production builds** to ensure reproducibility
3. **Keep env files in sync** - Document differences
4. **Use separate database volumes** for dev/prod (currently shared!)
5. **Regular cleanup** - Run `docker system prune` weekly
6. **Version control env examples** - Keep `.env.example` updated
7. **Enable MongoDB/Redis authentication** before public deployment

## Quick Reference

| Action | Dev Command | Prod Command |
|--------|-------------|--------------|
| Build | `docker-compose -f docker-compose.dev.yml build` | `docker-compose -f docker-compose.prod.yml build --no-cache` |
| Start | `docker-compose -f docker-compose.dev.yml up -d` | `docker-compose -f docker-compose.prod.yml up -d` |
| Stop | `docker-compose -f docker-compose.dev.yml down` | `docker-compose -f docker-compose.prod.yml down` |
| Logs | `docker-compose -f docker-compose.dev.yml logs -f` | `docker-compose -f docker-compose.prod.yml logs -f` |
| Restart | `docker-compose -f docker-compose.dev.yml restart` | `docker-compose -f docker-compose.prod.yml restart` |


