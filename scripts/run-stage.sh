#!/bin/bash
# Helper script to run production builds locally for verification
# This script loads .env.stage and runs docker-compose.prod.yml

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if .env.stage exists
ENV_STAGE_FILE="$PROJECT_ROOT/.env.stage"
if [ ! -f "$ENV_STAGE_FILE" ]; then
    echo "❌ Error: .env.stage file not found!"
    echo ""
    echo "Please create .env.stage in the project root with the following variables:"
    echo "  BACKEND_URL=http://localhost:8000"
    echo "  PAYLOAD_PUBLIC_SERVER_URL=http://localhost:3001"
    echo "  FRONTEND_URL=http://localhost:3000"
    echo "  NEXT_PUBLIC_BACKEND_URL=http://localhost:8000"
    echo "  NEXT_PUBLIC_PAYLOAD_URL=http://localhost:3001"
    echo "  CORS_ORIGINS=http://localhost:3000,http://localhost:3001"
    echo ""
    echo "See docs/STAGING.md for more details."
    exit 1
fi

# Change to project root
cd "$PROJECT_ROOT"

# Check for existing containers that might conflict
echo "🔍 Checking for existing containers..."
EXISTING_CONTAINERS=$(docker ps -a --filter "name=litecoin-" --format "{{.Names}}" 2>/dev/null || true)
if [ -n "$EXISTING_CONTAINERS" ]; then
    echo "⚠️  Warning: Found existing containers that may conflict:"
    echo "$EXISTING_CONTAINERS" | sed 's/^/   - /'
    echo ""
    echo "💡 Tip: Stop existing containers first with:"
    echo "   docker-compose -f docker-compose.prod.yml down"
    echo "   docker-compose -f docker-compose.dev.yml down"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted. Please stop existing containers first."
        exit 1
    fi
fi

# Export variables from .env.stage and run docker-compose
echo "📦 Loading environment variables from .env.stage..."
echo "🚀 Starting staging environment with production builds..."
echo ""

# Export variables (handle comments and empty lines)
export $(grep -v '^#' "$ENV_STAGE_FILE" | grep -v '^$' | xargs)

# Run docker-compose with production file
docker-compose -f docker-compose.prod.yml up --build "$@"

