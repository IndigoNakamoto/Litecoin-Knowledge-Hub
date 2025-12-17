#!/bin/bash
# =============================================================================
# Test Environment Helper Script
# =============================================================================
# Starts the test environment which:
#   - Shares Payload CMS database with production (real articles)
#   - Uses separate MongoDB for backend vector store
#   - Uses separate Redis for caching
#
# Usage:
#   ./scripts/run-test.sh           # Start in foreground (see logs)
#   ./scripts/run-test.sh -d        # Start in detached mode
#   ./scripts/run-test.sh down      # Stop test environment
#
# Port Mapping:
#   Backend:     http://localhost:8001  (vs production 8000)
#   Payload CMS: http://localhost:3002  (vs production 3001)
#   Frontend:    http://localhost:3004  (vs production 3000)
#   MongoDB:     localhost:27018        (vs production 27017)
#   Redis:       localhost:6380         (vs production 6379)

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
# Check .env.test exists
# =============================================================================
ENV_TEST_FILE="$PROJECT_ROOT/.env.test"
if [ ! -f "$ENV_TEST_FILE" ]; then
    echo "⚠️  Warning: .env.test file not found!"
    echo ""
    echo "Please create .env.test from the example template:"
    echo "  cp .env.test.example .env.test"
    echo ""
    echo "Then configure PROD_DATABASE_URI to point to your production MongoDB"
    echo "for the payload_cms database."
    echo ""
    exit 1
fi

# =============================================================================
# Validate PROD_DATABASE_URI is configured
# =============================================================================
if ! grep -q "^PROD_DATABASE_URI=" "$ENV_TEST_FILE" 2>/dev/null; then
    echo "❌ Error: PROD_DATABASE_URI not found in .env.test"
    echo ""
    echo "Please add PROD_DATABASE_URI to .env.test pointing to your production MongoDB."
    echo "Example: PROD_DATABASE_URI=mongodb://user:pass@host:27017/payload_cms?authSource=admin"
    exit 1
fi

# Check if it's still the placeholder value
if grep -q "PROD_DATABASE_URI=mongodb://your-prod" "$ENV_TEST_FILE" 2>/dev/null; then
    echo "❌ Error: PROD_DATABASE_URI not configured in .env.test"
    echo ""
    echo "Please update PROD_DATABASE_URI in .env.test with your actual production MongoDB URI."
    echo "Example: PROD_DATABASE_URI=mongodb://user:pass@host:27017/payload_cms?authSource=admin"
    exit 1
fi

echo "✅ Found .env.test with PROD_DATABASE_URI configured"

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
echo "📋 Service URLs:"
echo "   Backend API:  http://localhost:8001"
echo "   Payload CMS:  http://localhost:3002"
echo "   Frontend:     http://localhost:3004"
echo ""
echo "🗄️  Data Isolation:"
echo "   MongoDB (test): localhost:27018 - Vector store only"
echo "   Redis (test):   localhost:6380  - Cache only"
echo ""
echo "⚠️  IMPORTANT:"
echo "   Payload CMS is connected to PRODUCTION MongoDB!"
echo "   Any article edits will affect PRODUCTION data."
echo ""

# Start services with any additional arguments (e.g., -d for detached)
$DOCKER_COMPOSE -f docker-compose.test.yml up "$@"

