#!/bin/bash
# Script to reset all metrics: Prometheus, Redis, and backend cost totals
# This provides a complete fresh start for metrics tracking

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

echo "🔄 Resetting all metrics and cost tracking..."
echo ""

# 1. Clear Prometheus data
echo "1️⃣  Clearing Prometheus data..."
if docker ps --format '{{.Names}}' | grep -q "^litecoin-prometheus$"; then
    $DOCKER_COMPOSE -f docker-compose.prod.yml stop prometheus || true
    docker volume rm litecoin-knowledge-hub_prometheus_data 2>/dev/null || echo "   Prometheus volume doesn't exist"
    $DOCKER_COMPOSE -f docker-compose.prod.yml up -d prometheus
    echo "   ✅ Prometheus data cleared"
else
    echo "   ⏭️  Prometheus not running, skipping"
fi

# 2. Clear Redis spend tracking
echo ""
echo "2️⃣  Clearing Redis spend tracking..."
if docker ps --format '{{.Names}}' | grep -q "redis"; then
    REDIS_CONTAINER=$(docker ps --format '{{.Names}}' | grep redis | head -1)
    docker exec "$REDIS_CONTAINER" redis-cli FLUSHDB 2>/dev/null || echo "   ⚠️  Could not clear Redis (may not be needed)"
    echo "   ✅ Redis spend tracking cleared"
else
    echo "   ⏭️  Redis not running, skipping"
fi

# 3. Reset backend cost totals JSON file
echo ""
echo "3️⃣  Resetting backend cost totals..."
COST_TOTALS_FILE="backend/monitoring/data/llm_cost_totals.json"
if [ -f "$COST_TOTALS_FILE" ]; then
    rm "$COST_TOTALS_FILE"
    echo "   ✅ Cost totals file removed"
else
    echo "   ⏭️  Cost totals file doesn't exist"
fi

# 4. Restart backend to reload with fresh metrics
echo ""
echo "4️⃣  Restarting backend to reload metrics..."
$DOCKER_COMPOSE -f docker-compose.prod.yml restart backend || echo "   ⚠️  Could not restart backend"

echo ""
echo "✅ All metrics reset complete!"
echo ""
echo "📊 Next steps:"
echo "   1. Wait for backend to restart (~30 seconds)"
echo "   2. Make some test requests to generate new metrics"
echo "   3. Check Grafana dashboard: http://localhost:3002"
echo ""

