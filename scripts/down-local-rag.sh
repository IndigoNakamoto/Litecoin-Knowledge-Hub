#!/bin/bash
# =============================================================================
# Local RAG Services Shutdown Script
# =============================================================================
# Stops all local RAG services (Redis Stack, Ollama, and Infinity).
#
# Usage:
#   ./scripts/down-local-rag.sh         # Stop services, keep data
#   ./scripts/down-local-rag.sh -v      # Stop services and remove volumes
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect Docker Compose command
if docker compose version &>/dev/null; then
    DOCKER_COMPOSE="docker compose"
elif docker-compose version &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}❌ Error: Docker Compose not found!${NC}"
    exit 1
fi

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}🛑 Stopping Local RAG Services${NC}"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# =============================================================================
# Stop Native Embedding Server (if running)
# =============================================================================
if [ -f "$PROJECT_ROOT/.infinity.pid" ]; then
    PID=$(cat "$PROJECT_ROOT/.infinity.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${BLUE}🍎 Stopping native embedding server (PID: $PID)...${NC}"
        kill "$PID" 2>/dev/null || true
        sleep 2
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null || true
        fi
        echo -e "${GREEN}   ✓ Native embedding server stopped${NC}"
    else
        echo -e "${YELLOW}   Native embedding server not running (stale PID file)${NC}"
    fi
    rm -f "$PROJECT_ROOT/.infinity.pid"
fi

# Also check for any stray embedding server processes
STRAY_PIDS=$(pgrep -f "embeddings_server.py" 2>/dev/null || true)
if [ -n "$STRAY_PIDS" ]; then
    echo -e "${YELLOW}   Cleaning up stray embedding server processes...${NC}"
    echo "$STRAY_PIDS" | xargs kill 2>/dev/null || true
fi

# =============================================================================
# Stop Docker Services
# =============================================================================
echo ""
echo -e "${BLUE}🐳 Stopping Docker services...${NC}"

# Provide dummy values for required env vars (for docker-compose parsing)
export GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-dummy-for-shutdown}"

# Build compose files argument
COMPOSE_FILES="-f docker-compose.prod.yml"
if [ -f "docker-compose.override.yml" ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.override.yml"
fi

# Stop local-rag profile services
$DOCKER_COMPOSE $COMPOSE_FILES --profile local-rag stop redis_stack ollama infinity 2>/dev/null || true

# Remove containers (pass through -v if specified)
$DOCKER_COMPOSE $COMPOSE_FILES --profile local-rag rm -f redis_stack ollama infinity "$@" 2>/dev/null || true

echo -e "${GREEN}   ✓ Docker services stopped${NC}"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}✅ Local RAG services stopped!${NC}"
echo ""

if [[ "$*" == *"-v"* ]]; then
    echo -e "${YELLOW}⚠️  Volumes were removed. Model cache will need to be re-downloaded.${NC}"
else
    echo -e "${BLUE}💡 Data volumes preserved. To remove them:${NC}"
    echo -e "   ./scripts/down-local-rag.sh -v"
fi
echo ""
echo -e "${BLUE}💡 To restart local RAG services:${NC}"
echo -e "   ./scripts/run-local-rag.sh"

