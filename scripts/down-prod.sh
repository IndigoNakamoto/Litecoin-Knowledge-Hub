#!/bin/bash
# Simple script to shutdown production services using docker-compose.prod.yml and docker-compose.override.yml
# Also stops local RAG services (native embedding server, Ollama, Redis Stack) if running

set -e

# Detect Docker Compose command (v2 uses 'docker compose', v1 uses 'docker-compose')
if docker compose version &>/dev/null; then
    DOCKER_COMPOSE="docker compose"
elif docker-compose version &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Error: Docker Compose not found!"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Check if docker-compose.prod.yml exists
PROD_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
if [ ! -f "$PROD_COMPOSE_FILE" ]; then
  echo "❌ Error: docker-compose.prod.yml file not found!"
  exit 1
fi

# Check if docker-compose.override.yml exists (use if available)
OVERRIDE_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.override.yml"
if [ -f "$OVERRIDE_COMPOSE_FILE" ]; then
  COMPOSE_FILES="-f docker-compose.prod.yml -f docker-compose.override.yml"
else
  COMPOSE_FILES="-f docker-compose.prod.yml"
fi

echo "🛑 Shutting down production services..."
echo ""

# =============================================================================
# Stop Native Embedding Server (if running)
# =============================================================================
if [ -f "$PROJECT_ROOT/.infinity.pid" ]; then
    PID=$(cat "$PROJECT_ROOT/.infinity.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo "🍎 Stopping native embedding server (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 2
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null || true
        fi
        echo "   ✓ Native embedding server stopped"
    fi
    rm -f "$PROJECT_ROOT/.infinity.pid"
fi

# Also check for any stray embedding server processes
STRAY_PIDS=$(pgrep -f "embeddings_server.py" 2>/dev/null || true)
if [ -n "$STRAY_PIDS" ]; then
    echo "   Cleaning up stray embedding server processes..."
    echo "$STRAY_PIDS" | xargs kill 2>/dev/null || true
fi

# For shutdown operations, docker-compose needs to parse the entire config file
# If GRAFANA_ADMIN_PASSWORD is not set, provide a temporary dummy value
# This only affects parsing - no services will start during shutdown
if [ -z "${GRAFANA_ADMIN_PASSWORD:-}" ]; then
  export GRAFANA_ADMIN_PASSWORD="dummy-for-shutdown-only"
  echo "⚠️  Note: GRAFANA_ADMIN_PASSWORD not set, using temporary value for shutdown parsing"
  echo ""
fi

# Shutdown main production services (pass through any additional arguments like -v for volumes)
$DOCKER_COMPOSE $COMPOSE_FILES down "$@"

# Also stop local-rag profile services if they're running
echo ""
echo "🔍 Checking for local RAG services..."
if docker ps --format '{{.Names}}' | grep -q "litecoin-ollama\|litecoin-redis-stack"; then
    echo "   Stopping local RAG Docker services..."
    $DOCKER_COMPOSE $COMPOSE_FILES --profile local-rag down "$@" 2>/dev/null || true
    echo "   ✓ Local RAG Docker services stopped"
else
    echo "   No local RAG Docker services running"
fi

echo ""
echo "🧹 Cleaning up dangling images from previous builds..."
docker image prune -f > /dev/null 2>&1
echo "   ✓ Cleaned up dangling images"
echo ""

echo "✅ All services shutdown complete!"
echo "   (Production services + Local RAG services)"
echo ""
echo "💡 Tip: To free up more disk space, run:"
echo "   docker system prune -a        # Remove all unused images, containers, networks"
echo "   docker builder prune -a       # Remove build cache"

