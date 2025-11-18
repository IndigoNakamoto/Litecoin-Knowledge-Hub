# Environment Variables Documentation

This document describes all environment variables used in the Litecoin Knowledge Hub project and where they should be configured.

## Environment File Structure

The project uses a centralized environment variable management system:

### Root-Level Environment Files

- **`.env.example`** - Template with all variables documented (committed to git)
- **`.env.local`** - Local development (localhost URLs) - NOT in git
- **`.env.docker.dev`** - Docker development (service names) - NOT in git
- **`.env.docker.prod`** - Docker production (service names, production URLs) - NOT in git
- **`.env.prod-local`** - Local production build verification - NOT in git

### Service-Specific Environment Files

These files contain **secrets only** and should NOT be committed to git:

- **`backend/.env`** - Backend secrets (GOOGLE_API_KEY, etc.)
- **`payload_cms/.env`** - Payload CMS secrets (PAYLOAD_SECRET, etc.)

## Variable Categories

### 1. Service URLs

These variables differ based on the environment (localhost vs Docker service names vs production URLs).

| Variable | Local Dev | Docker Dev | Docker Prod | Description |
|----------|-----------|------------|-------------|-------------|
| `BACKEND_URL` | `http://localhost:8000` | `http://litecoin-backend:8000` | `http://litecoin-backend:8000` | Backend API URL (internal) |
| `PAYLOAD_PUBLIC_SERVER_URL` | `http://localhost:3001` | `http://localhost:3001` | `https://cms.lite.space` | Payload CMS public URL |
| `FRONTEND_URL` | `http://localhost:3000` | `http://localhost:3000` | `https://chat.lite.space` | Frontend URL (for CORS/CSRF) |
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | `http://localhost:8000` | `https://api.lite.space` | Backend URL exposed to browser |
| `NEXT_PUBLIC_PAYLOAD_URL` | `http://localhost:3001` | `http://localhost:3001` | `https://cms.lite.space` | Payload URL exposed to browser |

**Where to set:** Root-level `.env.*` files

### 2. Database Connections

These variables use different hostnames based on the environment.

| Variable | Local Dev | Docker | Description |
|----------|-----------|--------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017` | `mongodb://mongodb:27017` | MongoDB connection string |
| `MONGO_DETAILS` | `mongodb://localhost:27017` | `mongodb://mongodb:27017` | MongoDB details (alias) |
| `MONGODB_URI` | `mongodb://localhost:27017` | `mongodb://mongodb:27017` | MongoDB URI (alias) |
| `TEST_MONGO_URI` | `mongodb://localhost:27017` | `mongodb://mongodb:27017` | Test MongoDB URI |
| `DATABASE_URI` | `mongodb://localhost:27017/payload_cms` | `mongodb://mongodb:27017/payload_cms` | Payload CMS database URI |
| `REDIS_URL` | `redis://localhost:6379/0` | `redis://redis:6379/0` | Redis connection URL |

**Where to set:** Root-level `.env.*` files

### 3. Secrets

These should be stored in service-specific `.env` files and never committed to git.

| Variable | Service | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | Backend | Google AI API key for Gemini |
| `PAYLOAD_SECRET` | Payload CMS | Payload CMS secret key |
| `WEBHOOK_SECRET` | Both | Shared secret for webhook HMAC signature verification (must be same in both services) |
| `CLOUDFLARE_TUNNEL_TOKEN` | Production | Cloudflare tunnel token (optional) |

**Where to set:** 
- `backend/.env` for `GOOGLE_API_KEY` and `WEBHOOK_SECRET`
- `payload_cms/.env` for `PAYLOAD_SECRET` and `WEBHOOK_SECRET`
- Root `.env.docker.prod` or environment variables for `CLOUDFLARE_TUNNEL_TOKEN`

**Important:** `WEBHOOK_SECRET` must be the same value in both `backend/.env` and `payload_cms/.env` for webhook authentication to work. Generate a secure random string:

```bash
# Using OpenSSL
openssl rand -base64 32

# Or using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"

# Or using Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Configuration

These variables are usually the same across environments but can be overridden.

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_DB_NAME` | `litecoin_rag_db` | MongoDB database name |
| `MONGO_COLLECTION_NAME` | `litecoin_docs` | MongoDB collection for RAG documents |
| `MONGO_DATABASE_NAME` | `litecoin_rag_db` | MongoDB database name (alias) |
| `CMS_ARTICLES_COLLECTION_NAME` | `cms_articles` | CMS articles collection name |
| `EMBEDDING_MODEL` | `text-embedding-004` | Embedding model name |
| `CORS_ORIGINS` | Varies by env | CORS allowed origins (comma-separated) |
| `RATE_LIMIT_PER_MINUTE` | `20` | Rate limit per minute |
| `RATE_LIMIT_PER_HOUR` | `300` | Rate limit per hour |
| `LOG_LEVEL` | `INFO` | Logging level |
| `JSON_LOGGING` | `false` | Enable JSON logging format |
| `NODE_ENV` | `development` | Node.js environment |

**Where to set:** Root-level `.env.*` files

### 5. Monitoring (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_ADMIN_USER` | `admin` | Grafana admin username |
| `GRAFANA_ADMIN_PASSWORD` | `admin` | Grafana admin password |

**Where to set:** Root-level `.env.*` files

### 6. Docker-Specific

| Variable | Default | Description |
|----------|---------|-------------|
| `WATCHPACK_POLLING` | `true` | Enable file watching in Docker |
| `HOSTNAME` | `0.0.0.0` | Hostname for Next.js in Docker |

**Where to set:** Root-level `.env.docker.*` files

## Setup Instructions

### For Local Development

1. Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```

2. Update `.env.local` with localhost URLs (already set in template)

3. Create service-specific `.env` files:
   ```bash
   # Generate a secure webhook secret (use the same value in both files)
   WEBHOOK_SECRET=$(openssl rand -base64 32)
   
   # Backend secrets
   echo "GOOGLE_API_KEY=your-key-here" > backend/.env
   echo "WEBHOOK_SECRET=$WEBHOOK_SECRET" >> backend/.env
   
   # Payload CMS secrets
   echo "PAYLOAD_SECRET=your-secret-here" > payload_cms/.env
   echo "WEBHOOK_SECRET=$WEBHOOK_SECRET" >> payload_cms/.env
   ```

### For Docker Development

1. Copy `.env.example` to `.env.docker.dev`:
   ```bash
   cp .env.example .env.docker.dev
   ```

2. The `.env.docker.dev` file already has Docker service names configured

3. Ensure service-specific `.env` files exist (same as local development)

4. Run with:
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

### For Docker Production

1. Copy `.env.example` to `.env.docker.prod`:
   ```bash
   cp .env.example .env.docker.prod
   ```

2. Update production URLs in `.env.docker.prod`:
   - `PAYLOAD_PUBLIC_SERVER_URL=https://cms.lite.space`
   - `FRONTEND_URL=https://chat.lite.space`
   - `NEXT_PUBLIC_BACKEND_URL=https://api.lite.space`
   - `NEXT_PUBLIC_PAYLOAD_URL=https://cms.lite.space`

3. Ensure service-specific `.env` files have production secrets

4. Run with:
   ```bash
   docker-compose -f docker-compose.prod.yml up
   ```

### For Local Production Build Verification

1. Create `.env.prod-local`:
   ```bash
   cp .env.example .env.prod-local
   ```

2. Update with localhost URLs for local access

3. Run with:
   ```bash
   ./scripts/run-prod-local.sh
   ```

## Variable Precedence

When using docker-compose, environment variables are loaded in this order (later values override earlier ones):

1. Root-level `.env.*` file (e.g., `.env.docker.dev`)
2. Service-specific `.env` file (e.g., `backend/.env`)
3. `environment:` section in docker-compose.yml (highest priority)

## Best Practices

1. **Never commit secrets to git** - Use service-specific `.env` files for secrets
2. **Use `.env.example` as a template** - Always update it when adding new variables
3. **Document new variables** - Add them to this file and `.env.example`
4. **Use appropriate files** - Don't mix local and Docker configurations
5. **Test in each environment** - Verify variables work in local, Docker dev, and production

## Troubleshooting

### Variables not loading in Docker

- Check that the `.env.*` file exists in the project root
- Verify the `env_file` section in docker-compose.yml points to the correct file
- Ensure variable names match exactly (case-sensitive)

### Wrong URLs in production

- Verify `.env.docker.prod` has production URLs
- Check that `NEXT_PUBLIC_*` variables are set correctly (these are baked into the frontend build)
- For frontend, rebuild the Docker image after changing `NEXT_PUBLIC_*` variables

### Secrets not working

- Ensure service-specific `.env` files exist (e.g., `backend/.env`)
- Verify the files are not in `.gitignore` (they should be)
- Check that variable names match what the service expects

