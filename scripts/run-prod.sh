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
  echo "See docs/ENVIRONMENT_VARIABLES.md for details."
  echo ""
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted. Please create .env.docker.prod first."
    exit 1
  fi
else
  echo "📦 Loading environment variables from .env.docker.prod..."
  # Export variables (handle comments and empty lines)
  set -a  # Automatically export all variables
  source <(grep -v '^#' "$ENV_PROD_FILE" | grep -v '^$' | sed 's/^/export /')
  set +a  # Stop automatically exporting
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

# Set production URLs (defaults from docker-compose.prod.yml)
PROD_BACKEND_URL="${NEXT_PUBLIC_BACKEND_URL:-https://api.lite.space}"
PROD_PAYLOAD_URL="${NEXT_PUBLIC_PAYLOAD_URL:-https://cms.lite.space}"

echo "🔧 Using production build configuration:"
echo "   NEXT_PUBLIC_BACKEND_URL=$PROD_BACKEND_URL"
echo "   NEXT_PUBLIC_PAYLOAD_URL=$PROD_PAYLOAD_URL"
echo ""
echo "🔨 Building all services with --no-cache (clean rebuild)..."
echo "   This ensures all dependencies are freshly installed and"
echo "   NEXT_PUBLIC_* variables are correctly baked into the frontend build."
echo ""

# Build all services with --no-cache, explicitly passing build args for frontend
# Note: "$@" is intentionally excluded from build command to ensure --no-cache cannot be overridden
$DOCKER_COMPOSE -f docker-compose.prod.yml build --no-cache \
  --build-arg NEXT_PUBLIC_BACKEND_URL="$PROD_BACKEND_URL" \
  --build-arg NEXT_PUBLIC_PAYLOAD_URL="$PROD_PAYLOAD_URL"

echo ""
echo "✅ Build complete!"
echo ""

# Setup cron job for suggested question cache refresh (optional)
setup_cron_job() {
    # Skip if running inside Docker
    if [ -f /.dockerenv ]; then
        echo "⏭️  Skipping cron job setup (running inside Docker)"
        return
    fi
    
    # Check if cron is available
    if ! command -v crontab &> /dev/null; then
        echo "⚠️  Cron is not available, skipping cron job setup"
        return
    fi
    
    # Get absolute path to the refresh script
    REFRESH_SCRIPT="$PROJECT_ROOT/scripts/refresh-suggested-cache.sh"
    
    # Check if refresh script exists
    if [ ! -f "$REFRESH_SCRIPT" ]; then
        echo "⚠️  Refresh script not found at $REFRESH_SCRIPT, skipping cron job setup"
        return
    fi
    
    # Check if ADMIN_TOKEN is set in backend/.env
    if [ ! -f "$PROJECT_ROOT/backend/.env" ] || ! grep -q "ADMIN_TOKEN" "$PROJECT_ROOT/backend/.env"; then
        echo "⚠️  ADMIN_TOKEN not found in backend/.env"
        echo "   Cron job setup skipped. Set ADMIN_TOKEN to enable automatic cache refresh."
        return
    fi
    
    # Check if cron job already exists
    CRON_CMD="0 2 */2 * * $REFRESH_SCRIPT"
    if crontab -l 2>/dev/null | grep -qF "$REFRESH_SCRIPT"; then
        echo "✅ Cron job for suggested question cache refresh already exists"
        echo "   To view: crontab -l"
        echo "   To remove: crontab -e (then delete the line)"
        return
    fi
    
    # Ask for confirmation
    echo "📅 Suggested Question Cache Refresh Cron Job Setup"
    echo ""
    echo "   This will add a cron job to refresh the suggested question cache"
    echo "   every 48 hours (every 2 days at 2:00 AM UTC)."
    echo ""
    echo "   Cron job command:"
    echo "   $CRON_CMD"
    echo ""
    read -p "   Set up cron job? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "⏭️  Skipping cron job setup"
        return
    fi
    
    # Create log directory if it doesn't exist
    LOG_DIR="/var/log"
    if [ ! -w "$LOG_DIR" ]; then
        LOG_DIR="$PROJECT_ROOT"
        echo "⚠️  Cannot write to /var/log, using project root for logs"
    fi
    
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_CMD >> $LOG_DIR/suggested-cache-refresh.log 2>&1") | crontab -
    
    if [ $? -eq 0 ]; then
        echo "✅ Cron job added successfully!"
        echo "   View with: crontab -l"
        echo "   Logs will be written to: $LOG_DIR/suggested-cache-refresh.log"
    else
        echo "❌ Failed to add cron job. You may need to run with appropriate permissions."
    fi
}

# Offer to set up cron job
setup_cron_job

echo ""
echo "🚀 Starting services..."
echo ""

# Start services (pass through any additional arguments like -d for detached mode)
$DOCKER_COMPOSE -f docker-compose.prod.yml up "$@"

