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
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | `http://localhost:8000` | `https://api.lite.space` | Backend URL exposed to browser (used by frontend and admin frontend) |
| `NEXT_PUBLIC_PAYLOAD_URL` | `http://localhost:3001` | `http://localhost:3001` | `https://cms.lite.space` | Payload URL exposed to browser |
| `ADMIN_FRONTEND_URL` | `http://localhost:3003` | `http://localhost:3003` | `http://localhost:3003` (local) | Admin frontend URL - runs locally. Backend automatically adds this to CORS origins. Can also be added to CORS_ORIGINS if needed. |

**Where to set:** Root-level `.env.*` files

### 2. Database Connections

These variables use different hostnames based on the environment. **Authentication is required for production deployments** (see [MongoDB/Redis Authentication Migration Guide](./MONGODB_REDIS_AUTH_MIGRATION.md)).

| Variable | Local Dev | Docker (No Auth) | Docker (With Auth) | Description |
|----------|-----------|------------------|-------------------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017` | `mongodb://mongodb:27017` | `mongodb://litecoin_app:PASSWORD@mongodb:27017/litecoin_rag_db?authSource=litecoin_rag_db` | MongoDB connection string |
| `MONGO_DETAILS` | `mongodb://localhost:27017` | `mongodb://mongodb:27017` | `mongodb://litecoin_app:PASSWORD@mongodb:27017/litecoin_rag_db?authSource=litecoin_rag_db` | MongoDB details (alias) |
| `MONGODB_URI` | `mongodb://localhost:27017` | `mongodb://mongodb:27017` | `mongodb://litecoin_app:PASSWORD@mongodb:27017/litecoin_rag_db?authSource=litecoin_rag_db` | MongoDB URI (alias) |
| `TEST_MONGO_URI` | `mongodb://localhost:27017` | `mongodb://mongodb:27017` | `mongodb://litecoin_app:PASSWORD@mongodb:27017/litecoin_rag_db?authSource=litecoin_rag_db` | Test MongoDB URI |
| `DATABASE_URI` | `mongodb://localhost:27017/payload_cms` | `mongodb://mongodb:27017/payload_cms` | `mongodb://litecoin_app:PASSWORD@mongodb:27017/payload_cms?authSource=payload_cms` | Payload CMS database URI |
| `REDIS_URL` | `redis://localhost:6379/0` | `redis://redis:6379/0` | `redis://:PASSWORD@redis:6379/0` | Redis connection URL (used for rate limiting and suggested question cache) |

**Where to set:** Root-level `.env.*` files

**Note:** Replace `PASSWORD` with actual passwords from `MONGO_APP_PASSWORD` and `REDIS_PASSWORD` environment variables. The `authSource` parameter tells MongoDB which database to authenticate against.

### 3. Secrets

These should be stored in service-specific `.env` files and never committed to git.

| Variable | Service | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | Backend | Google AI API key for Gemini |
| `PAYLOAD_SECRET` | Payload CMS | Payload CMS secret key |
| `WEBHOOK_SECRET` | Both | Shared secret for webhook HMAC signature verification (must be same in both services) |
| `ADMIN_TOKEN` | Backend | Bearer token for admin endpoints (e.g., cache refresh) |
| `TURNSTILE_SECRET_KEY` | Backend | Cloudflare Turnstile secret key (required if `ENABLE_TURNSTILE=true`) |
| `CLOUDFLARE_TUNNEL_TOKEN` | Production | Cloudflare tunnel token (optional) |
| `MONGO_ROOT_USERNAME` | Docker | MongoDB root/admin username (default: `admin`) |
| `MONGO_ROOT_PASSWORD` | Docker | **REQUIRED** - MongoDB root/admin password (generate with `openssl rand -base64 32`) |
| `MONGO_APP_USERNAME` | Docker | MongoDB application username (default: `litecoin_app`) |
| `MONGO_APP_PASSWORD` | Docker | **REQUIRED** - MongoDB application user password (generate with `openssl rand -base64 32`) |
| `REDIS_PASSWORD` | Docker | **REQUIRED** - Redis password (generate with `openssl rand -base64 32`) |

**Where to set:** 
- `backend/.env` for `GOOGLE_API_KEY`, `WEBHOOK_SECRET`, and `ADMIN_TOKEN`
- `payload_cms/.env` for `PAYLOAD_SECRET` and `WEBHOOK_SECRET`
- Root `.env.docker.prod`, `.env.docker.dev`, or `.env.prod-local` for `MONGO_ROOT_PASSWORD`, `MONGO_APP_PASSWORD`, and `REDIS_PASSWORD`
- Root `.env.docker.prod` or environment variables for `CLOUDFLARE_TUNNEL_TOKEN`

**Important:** 
- `WEBHOOK_SECRET` must be the same value in both `backend/.env` and `payload_cms/.env` for webhook authentication to work.
- MongoDB and Redis authentication passwords are **REQUIRED for production deployments** (see [MongoDB/Redis Authentication Migration Guide](./MONGODB_REDIS_AUTH_MIGRATION.md)).

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
| `CORS_ORIGINS` | `http://localhost:3000,https://chat.lite.space,https://www.chat.lite.space` | CORS allowed origins (comma-separated). Default includes frontend URLs. In development, common localhost ports (3000-3003) are automatically added. The backend also automatically adds `ADMIN_FRONTEND_URL` to CORS origins if set. When running admin frontend locally against production backend, either set `ADMIN_FRONTEND_URL` or add the admin frontend URL to this variable. |
| `RATE_LIMIT_PER_MINUTE` | `20` | Rate limit per minute |
| `RATE_LIMIT_PER_HOUR` | `300` | Rate limit per hour |
| `PAYLOAD_URL` | `https://cms.lite.space` | Payload CMS URL for fetching suggested questions |
| `SUGGESTED_QUESTION_CACHE_TTL` | `86400` | Suggested question cache TTL in seconds (24 hours) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `JSON_LOGGING` | `false` | Enable JSON logging format |
| `NODE_ENV` | `development` | Node.js environment |
| `DAILY_SPEND_LIMIT_USD` | `5.00` | Daily LLM spend limit in USD |
| `HOURLY_SPEND_LIMIT_USD` | `1.00` | Hourly LLM spend limit in USD |
| `DISCORD_WEBHOOK_URL` | (none) | Discord webhook URL for spend limit alerts (optional) |
| `CHALLENGE_TTL_SECONDS` | `300` | Challenge TTL in seconds (5 minutes) for challenge-response fingerprinting |
| `CHALLENGE_RATE_LIMIT_PER_MINUTE` | `10` | Maximum challenges per IP per minute |
| `CHALLENGE_RATE_LIMIT_PER_HOUR` | `100` | Maximum challenges per IP per hour |
| `MAX_ACTIVE_CHALLENGES_PER_IDENTIFIER` | `3` | Maximum active challenges per fingerprint/IP |
| `ENABLE_CHALLENGE_RESPONSE` | `true` | Enable challenge-response fingerprinting |
| `GLOBAL_RATE_LIMIT_PER_MINUTE` | `1000` | Global rate limit (aggregate requests per minute across all identifiers) |
| `GLOBAL_RATE_LIMIT_PER_HOUR` | `50000` | Global rate limit (aggregate requests per hour across all identifiers) |
| `ENABLE_GLOBAL_RATE_LIMIT` | `true` | Enable global rate limiting |
| `TURNSTILE_SECRET_KEY` | (none) | Cloudflare Turnstile secret key (required if `ENABLE_TURNSTILE=true`) |
| `ENABLE_TURNSTILE` | `false` | Enable Cloudflare Turnstile verification |
| `HIGH_COST_THRESHOLD_USD` | `10.0` | Cost threshold in USD that triggers throttling (per fingerprint in 10-minute window) |
| `HIGH_COST_WINDOW_SECONDS` | `600` | Cost tracking window in seconds (10 minutes) |
| `ENABLE_COST_THROTTLING` | `true` | Enable cost-based throttling |
| `COST_THROTTLE_DURATION_SECONDS` | `30` | Duration in seconds that a fingerprint is throttled after exceeding cost threshold |
| `TRUST_X_FORWARDED_FOR` | `false` | **SECURITY:** Set to `true` only when behind a trusted reverse proxy that strips user-supplied headers. When `false` (default), `X-Forwarded-For` is ignored to prevent IP spoofing attacks. Always use `CF-Connecting-IP` when behind Cloudflare (automatically trusted). See [Rate Limiting Security Guide](../security/RATE_LIMITING_SECURITY.md) for details. |

**Where to set:** Root-level `.env.*` files (for spend limits and abuse prevention features, set in `backend/.env`)

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
   
   # Generate admin token
   ADMIN_TOKEN=$(openssl rand -base64 32)
   
   # Backend secrets
   echo "GOOGLE_API_KEY=your-key-here" > backend/.env
   echo "WEBHOOK_SECRET=$WEBHOOK_SECRET" >> backend/.env
   echo "ADMIN_TOKEN=$ADMIN_TOKEN" >> backend/.env
   
   # Payload CMS secrets
   echo "PAYLOAD_SECRET=your-secret-here" > payload_cms/.env
   echo "WEBHOOK_SECRET=$WEBHOOK_SECRET" >> payload_cms/.env
   ```

### For Docker Development

1. Copy `.env.example` to `.env.docker.dev`:
   ```bash
   cp .env.example .env.docker.dev
   ```

2. Generate MongoDB and Redis passwords and add to `.env.docker.dev`:
   ```bash
   # Generate passwords
   MONGO_ROOT_PASSWORD=$(openssl rand -base64 32)
   MONGO_APP_PASSWORD=$(openssl rand -base64 32)
   REDIS_PASSWORD=$(openssl rand -base64 32)
   
   # Add to .env.docker.dev
   echo "MONGO_ROOT_PASSWORD=$MONGO_ROOT_PASSWORD" >> .env.docker.dev
   echo "MONGO_APP_PASSWORD=$MONGO_APP_PASSWORD" >> .env.docker.dev
   echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> .env.docker.dev
   
   # Update connection strings with passwords
   # (Edit .env.docker.dev manually to update MONGO_URI, DATABASE_URI, REDIS_URL)
   ```

3. The `.env.docker.dev` file already has Docker service names configured

4. Ensure service-specific `.env` files exist (same as local development)

5. **Before first run with authentication:** Create MongoDB users (see [MongoDB/Redis Authentication Migration Guide](./MONGODB_REDIS_AUTH_MIGRATION.md))

6. Run with:
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

### For Docker Production

1. Copy `.env.example` to `.env.docker.prod`:
   ```bash
   cp .env.example .env.docker.prod
   ```

2. Generate MongoDB and Redis passwords and add to `.env.docker.prod`:
   ```bash
   # Generate passwords
   MONGO_ROOT_PASSWORD=$(openssl rand -base64 32)
   MONGO_APP_PASSWORD=$(openssl rand -base64 32)
   REDIS_PASSWORD=$(openssl rand -base64 32)
   
   # Add to .env.docker.prod
   echo "MONGO_ROOT_PASSWORD=$MONGO_ROOT_PASSWORD" >> .env.docker.prod
   echo "MONGO_APP_PASSWORD=$MONGO_APP_PASSWORD" >> .env.docker.prod
   echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> .env.docker.prod
   ```

3. Update production URLs in `.env.docker.prod`:
   - `PAYLOAD_PUBLIC_SERVER_URL=https://cms.lite.space`
   - `FRONTEND_URL=https://chat.lite.space`
   - `NEXT_PUBLIC_BACKEND_URL=https://api.lite.space`
   - `NEXT_PUBLIC_PAYLOAD_URL=https://cms.lite.space`
   - `CORS_ORIGINS=https://chat.lite.space,https://www.chat.lite.space` (or set `ADMIN_FRONTEND_URL=http://localhost:3003` to automatically add admin frontend to CORS)

4. Update connection strings in `.env.docker.prod` with authentication:
   - `MONGO_URI=mongodb://litecoin_app:${MONGO_APP_PASSWORD}@mongodb:27017/litecoin_rag_db?authSource=litecoin_rag_db`
   - `MONGO_DETAILS=mongodb://litecoin_app:${MONGO_APP_PASSWORD}@mongodb:27017/litecoin_rag_db?authSource=litecoin_rag_db`
   - `DATABASE_URI=mongodb://litecoin_app:${MONGO_APP_PASSWORD}@mongodb:27017/payload_cms?authSource=payload_cms`
   - `REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0`

5. Ensure service-specific `.env` files have production secrets

6. **Before first run with authentication:** Create MongoDB users (see [MongoDB/Redis Authentication Migration Guide](./MONGODB_REDIS_AUTH_MIGRATION.md))

7. Run with:
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

