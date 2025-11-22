#!/bin/bash
# Script to clean test articles from the vector store
# This should be run inside the backend Docker container

set -e

# Detect if we're in Docker or running locally
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    echo "🐳 Running inside Docker container..."
    # We're already in the container, run the script directly
    python backend/utils/clean_test_articles.py "$@"
else
    # Check if backend container is running (try both dev and prod container names)
    BACKEND_CONTAINER=""
    if docker ps --format '{{.Names}}' | grep -q "litecoin-backend-dev"; then
        BACKEND_CONTAINER="litecoin-backend-dev"
    elif docker ps --format '{{.Names}}' | grep -q "litecoin-backend"; then
        BACKEND_CONTAINER="litecoin-backend"
    fi
    
    if [ -n "$BACKEND_CONTAINER" ]; then
        echo "🐳 Running cleanup script inside backend container: $BACKEND_CONTAINER"
        docker exec -it "$BACKEND_CONTAINER" python backend/utils/clean_test_articles.py "$@"
    else
        echo "❌ ERROR: Backend container is not running."
        echo ""
        echo "📋 To fix this:"
        echo ""
        echo "1. Start your development environment:"
        echo "   ./scripts/run-dev.sh"
        echo ""
        echo "2. Once containers are running, run this script again:"
        echo "   ./scripts/clean-test-articles.sh --dry-run"
        echo ""
        echo "3. Or run directly in the container:"
        echo "   docker exec -it litecoin-backend-dev python backend/utils/clean_test_articles.py --dry-run"
        echo ""
        echo "📦 Checking for stopped containers..."
        STOPPED=$(docker ps -a --format '{{.Names}}' | grep -E "litecoin-backend" | head -1 || echo "")
        if [ -n "$STOPPED" ]; then
            echo "   Found stopped container: $STOPPED"
            echo "   You can start it with: docker start $STOPPED"
        fi
        exit 1
    fi
fi

