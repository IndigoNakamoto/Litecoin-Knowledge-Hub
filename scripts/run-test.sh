#!/bin/bash
# =============================================================================
# Test Environment Helper Script
# =============================================================================
# Starts a test backend environment which:
#   - Uses your already-running production Payload CMS (localhost:3001)
#   - Uses separate MongoDB for backend vector store (isolated)
#   - Uses separate Redis for caching (isolated)
#
# PREREQUISITE: Production must be running first!
#   ./scripts/run-prod.sh -d
#
# Usage:
#   ./scripts/run-test.sh           # Start in foreground (see logs)
#   ./scripts/run-test.sh -d        # Start in detached mode
#   ./scripts/run-test.sh down      # Stop test environment
#
# Port Mapping:
#   Test Backend:  http://localhost:8001  (vs production 8000)
#   Test Frontend: http://localhost:3004  (vs production 3000)
#   Test MongoDB:  localhost:27018        (isolated from production)
#   Test Redis:    localhost:6381         (isolated from production)
#
# Uses Production:
#   Payload CMS:   http://localhost:3001  (production - shared)

set -e

# =============================================================================
# Setup
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

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

# Change to project root
cd "$PROJECT_ROOT"

# =============================================================================
# Handle 'down' command
# =============================================================================
if [ "$1" == "down" ]; then
    echo "🛑 Stopping test environment..."
    $DOCKER_COMPOSE -f docker-compose.test.yml down
    echo "✅ Test environment stopped."
    exit 0
fi

# =============================================================================
# Check that production Payload CMS is running
# =============================================================================
echo "🔍 Checking if production Payload CMS is running..."
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 | grep -q "200\|301\|302"; then
    echo "❌ Error: Production Payload CMS not running at localhost:3001"
    echo ""
    echo "The test environment uses your production Payload CMS for articles."
    echo "Please start production first:"
    echo "  ./scripts/run-prod.sh -d"
    echo ""
    exit 1
fi
echo "✅ Production Payload CMS is running at localhost:3001"

# =============================================================================
# Check for existing test containers
# =============================================================================
echo "🔍 Checking for existing test containers..."
EXISTING_CONTAINERS=$(docker ps -a --filter "name=litecoin-.*-test" --format "{{.Names}}" 2>/dev/null || true)
if [ -n "$EXISTING_CONTAINERS" ]; then
    echo "⚠️  Warning: Found existing test containers:"
    echo "$EXISTING_CONTAINERS" | sed 's/^/   - /'
    echo ""
    read -p "Stop and remove existing test containers? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $DOCKER_COMPOSE -f docker-compose.test.yml down
        echo "✅ Existing test containers removed."
    fi
fi

# =============================================================================
# Start test environment
# =============================================================================
echo ""
echo "🧪 Starting test environment..."
echo ""
echo "📋 Test Service URLs:"
echo "   Test Backend:  http://localhost:8001"
echo "   Test Frontend: http://localhost:3004"
echo ""
echo "📋 Production Services (shared):"
echo "   Payload CMS:   http://localhost:3001 (production)"
echo ""
echo "🗄️  Data Isolation:"
echo "   Test MongoDB:  localhost:27018 - Vector store (isolated)"
echo "   Test Redis:    localhost:6381  - Cache (isolated)"
echo ""
echo "⚠️  IMPORTANT:"
echo "   Edits in Payload CMS (localhost:3001) affect PRODUCTION data."
echo "   The test backend will process webhooks with new chunking logic."
echo ""

# Start services with any additional arguments (e.g., -d for detached)
$DOCKER_COMPOSE -f docker-compose.test.yml up "$@"

