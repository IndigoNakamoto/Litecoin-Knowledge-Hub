#!/bin/bash
# Script to clear Prometheus data and reset metrics
# This will delete all historical Prometheus data to start fresh

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
cd "$PROJECT_ROOT"

echo "🧹 Clearing Prometheus data..."
echo ""

# Check if Prometheus container is running
if ! docker ps --format '{{.Names}}' | grep -q "^litecoin-prometheus$"; then
    echo "⚠️  Prometheus container is not running."
    echo "   Starting Prometheus container first..."
    $DOCKER_COMPOSE -f docker-compose.prod.yml up -d prometheus
    sleep 5
fi

# Clear Prometheus data using the lifecycle API
echo "📊 Clearing Prometheus TSDB data..."
curl -X POST http://localhost:9090/api/v1/admin/tsdb/clean_tombstones || echo "⚠️  Could not clean tombstones (may not be needed)"

# Delete the Prometheus volume data
echo "🗑️  Removing Prometheus volume data..."
$DOCKER_COMPOSE -f docker-compose.prod.yml stop prometheus || true
docker volume rm litecoin-knowledge-hub_prometheus_data 2>/dev/null || echo "   Volume doesn't exist or already removed"

# Restart Prometheus to recreate volume
echo "🔄 Restarting Prometheus..."
$DOCKER_COMPOSE -f docker-compose.prod.yml up -d prometheus

echo ""
echo "✅ Prometheus data cleared!"
echo ""
echo "💡 Note: You may also want to:"
echo "   1. Clear Redis spend tracking: docker exec litecoin-redis redis-cli FLUSHDB"
echo "   2. Reset backend cost totals: rm backend/monitoring/data/llm_cost_totals.json"
echo ""

