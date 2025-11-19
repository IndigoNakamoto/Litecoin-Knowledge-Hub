#!/bin/bash
# Script to fix Docker BuildKit I/O errors and clean up corrupted cache

set -e

echo "🔧 Docker BuildKit Cleanup and Fix Script"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

echo "📊 Checking Docker disk usage..."
docker system df
echo ""

# Stop any running containers
echo "🛑 Stopping any running containers..."
docker ps -q | xargs -r docker stop 2>/dev/null || true
echo ""

# Prune BuildKit cache (this fixes corrupted metadata)
echo "🧹 Pruning Docker BuildKit cache..."
docker buildx prune -af --volumes 2>/dev/null || {
    echo "⚠️  BuildKit prune failed, trying alternative method..."
    # Alternative: Reset BuildKit entirely
    docker buildx rm --all-inactive 2>/dev/null || true
}
echo ""

# Prune system to free up space
echo "🧹 Pruning unused Docker resources..."
docker system prune -af --volumes 2>/dev/null || true
echo ""

# Check disk space
echo "💾 Checking available disk space..."
df -h . | tail -1
echo ""

# Restart Docker BuildKit (if possible)
echo "🔄 Attempting to restart BuildKit..."
if command -v docker &> /dev/null; then
    # Try to reset BuildKit by removing and recreating default builder
    docker buildx ls 2>/dev/null | grep -q "default" && {
        echo "   Resetting default builder..."
        docker buildx rm default 2>/dev/null || true
        docker buildx create --name default --use 2>/dev/null || true
    }
fi
echo ""

echo "✅ Cleanup complete!"
echo ""
echo "💡 Next steps:"
echo "   1. If errors persist, try restarting Docker Desktop"
echo "   2. Check available disk space (need at least 10GB free)"
echo "   3. Try building again with: ./scripts/run-prod.sh"
echo ""

