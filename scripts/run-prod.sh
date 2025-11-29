#!/bin/bash
# Helper script to run production builds with --no-cache and rebuild
# This script uses docker-compose.prod.yml which loads .env.docker.prod

set -e

# Detect Docker Compose command (v2 uses 'docker compose', v1 uses 'docker-compose')
if docker compose version &>/dev/null; then
    DOCKER_COMPOSE="docker compose"
elif docker-compose version &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Error: Docker Compose not found!"
    echo "   Please install Docker Compose (v2: 'docker compose' or v1: 'docker-compose')"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if .env.docker.prod exists (optional but recommended)
ENV_PROD_FILE="$PROJECT_ROOT/.env.docker.prod"
if [ ! -f "$ENV_PROD_FILE" ]; then
  echo "⚠️  Warning: .env.docker.prod file not found!"
  echo ""
  echo "Production environment variables will use defaults from docker-compose.prod.yml"
  echo "or environment variables set in your shell."
  echo ""
  echo "To create .env.docker.prod:"
  echo "  cp .env.example .env.docker.prod"
  echo ""
  echo "See docs/setup/ENVIRONMENT_VARIABLES.md for details."
  echo ""
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted. Please create .env.docker.prod first."
    exit 1
  fi
else
  echo "📦 Loading environment variables from .env.docker.prod..."
  # Export all variables from .env file
  # Create a temporary file with filtered content (no comments, no empty lines)
  TEMP_ENV=$(mktemp)
  grep -v '^[[:space:]]*#' "$ENV_PROD_FILE" | grep -v '^[[:space:]]*$' > "$TEMP_ENV"
  
  # Source the filtered file - this is the most reliable method
  set -a  # Automatically export all variables
  source "$TEMP_ENV"
  set +a
  
  # Clean up temp file
  rm -f "$TEMP_ENV"
  
  # Verify critical variables are set
  if [ -z "${GRAFANA_ADMIN_PASSWORD:-}" ]; then
    echo "❌ Error: GRAFANA_ADMIN_PASSWORD is not set in .env.docker.prod"
    echo "   Please add: GRAFANA_ADMIN_PASSWORD=your-secure-password"
    echo ""
    echo "   Current file location: $ENV_PROD_FILE"
    echo "   To debug, check if the variable exists:"
    echo "   grep GRAFANA_ADMIN_PASSWORD $ENV_PROD_FILE"
    exit 1
  fi
  echo "   ✓ GRAFANA_ADMIN_PASSWORD is set (length: ${#GRAFANA_ADMIN_PASSWORD} chars)"
fi

# Check if docker-compose.prod.yml exists
PROD_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
if [ ! -f "$PROD_COMPOSE_FILE" ]; then
  echo "❌ Error: docker-compose.prod.yml file not found!"
  echo ""
  echo "This file should exist in the project root."
  exit 1
fi

# Change to project root
cd "$PROJECT_ROOT"

# Check for existing containers that might conflict
echo "🔍 Checking for existing containers..."
EXISTING_CONTAINERS=$(docker ps -a --filter "name=litecoin-" --format "{{.Names}}" 2>/dev/null | grep -v "prod-local\|dev" || true)
if [ -n "$EXISTING_CONTAINERS" ]; then
  echo "⚠️  Warning: Found existing production containers that may conflict:"
  echo "$EXISTING_CONTAINERS" | sed 's/^/   - /'
  echo ""
  echo "💡 Tip: Stop existing containers first with:"
  echo "   $DOCKER_COMPOSE -f docker-compose.prod.yml down"
  echo ""
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted. Please stop existing containers first."
    exit 1
  fi
fi

echo "🚀 Starting production build with --no-cache (clean rebuild)..."
echo ""

# Clean up dangling images from previous builds to save disk space
echo "🧹 Cleaning up dangling images from previous builds..."
docker image prune -f > /dev/null 2>&1
echo "   ✓ Cleaned up dangling images"
echo ""

# Set production URLs (defaults from docker-compose.prod.yml)
PROD_BACKEND_URL="${NEXT_PUBLIC_BACKEND_URL:-https://api.lite.space}"
PROD_PAYLOAD_URL="${NEXT_PUBLIC_PAYLOAD_URL:-https://cms.lite.space}"

echo "🔧 Using production build configuration:"
echo "   NEXT_PUBLIC_BACKEND_URL=$PROD_BACKEND_URL"
echo "   NEXT_PUBLIC_PAYLOAD_URL=$PROD_PAYLOAD_URL"
echo ""
echo "🔨 Building all services with --no-cache (clean rebuild)..."
echo "   This ensures all dependencies are freshly installed and"
echo "   NEXT_PUBLIC_* variables are correctly baked into the frontend builds."
echo ""

# Build all services with --no-cache, explicitly passing build args for frontend and admin-frontend
# Note: "$@" is intentionally excluded from build command to ensure --no-cache cannot be overridden
$DOCKER_COMPOSE -f docker-compose.prod.yml build --no-cache \
  --build-arg NEXT_PUBLIC_BACKEND_URL="$PROD_BACKEND_URL" \
  --build-arg NEXT_PUBLIC_PAYLOAD_URL="$PROD_PAYLOAD_URL"

echo ""
echo "✅ Build complete!"
echo ""

# Setup cron job for suggested question cache refresh (optional)
# Bypassed for production - cron job setup is disabled
setup_cron_job() {
    return
}

# Offer to set up cron job
setup_cron_job

echo ""
echo "🚀 Starting services..."
echo ""
echo "📋 Service URLs:"
echo "   Frontend: http://localhost:3000 (via Cloudflare)"
echo "   Backend API: http://localhost:8000 (via Cloudflare)"
echo "   Payload CMS: http://localhost:3001 (via Cloudflare)"
echo "   Grafana: http://localhost:3002 (local only)"
echo "   Admin Frontend: http://localhost:3003 (local only, not via Cloudflare)"
echo "   Prometheus: http://localhost:9090 (local only)"
echo ""

# Start services (pass through any additional arguments like -d for detached mode)
$DOCKER_COMPOSE -f docker-compose.prod.yml up "$@"

