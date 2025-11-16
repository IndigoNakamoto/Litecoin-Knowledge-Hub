#!/bin/bash

# Script to test MongoDB connection leak fixes
# This script monitors MongoDB connections and tests the application

set -e

echo "🔍 MongoDB Connection Leak Fix Testing"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Determine which compose file to use
if [ -f "docker-compose.prod.yml" ] && docker compose ps --format json 2>/dev/null | grep -q "litecoin-mongodb"; then
    COMPOSE_FILE="docker-compose.prod.yml"
    MONGO_CONTAINER="litecoin-mongodb"
    BACKEND_CONTAINER="litecoin-backend"
elif [ -f "docker-compose.dev.yml" ] && docker compose -f docker-compose.dev.yml ps --format json 2>/dev/null | grep -q "litecoin-mongodb-dev"; then
    COMPOSE_FILE="docker-compose.dev.yml"
    MONGO_CONTAINER="litecoin-mongodb-dev"
    BACKEND_CONTAINER="litecoin-backend-dev"
else
    echo -e "${YELLOW}⚠️  No running containers found. Using docker-compose.dev.yml as default.${NC}"
    COMPOSE_FILE="docker-compose.dev.yml"
    MONGO_CONTAINER="litecoin-mongodb-dev"
    BACKEND_CONTAINER="litecoin-backend-dev"
fi

echo -e "${GREEN}Using compose file: ${COMPOSE_FILE}${NC}"
echo ""

# Function to get MongoDB connection count
get_connection_count() {
    docker exec $MONGO_CONTAINER mongosh --quiet --eval "db.serverStatus().connections.current" 2>/dev/null || echo "0"
}

# Function to get MongoDB connection details
get_connection_details() {
    echo "Active connections:"
    docker exec $MONGO_CONTAINER mongosh --quiet --eval "db.serverStatus().connections" 2>/dev/null || echo "Unable to get connection details"
}

# Step 1: Restart containers
echo -e "${YELLOW}Step 1: Restarting Docker containers...${NC}"
if [ "$COMPOSE_FILE" = "docker-compose.prod.yml" ]; then
    docker compose -f $COMPOSE_FILE down
    docker compose -f $COMPOSE_FILE up -d
else
    docker compose -f $COMPOSE_FILE down
    docker compose -f $COMPOSE_FILE up -d
fi

echo "Waiting for services to be healthy..."
sleep 10

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to be ready..."
timeout=60
elapsed=0
while ! docker exec $MONGO_CONTAINER mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1; do
    if [ $elapsed -ge $timeout ]; then
        echo -e "${RED}❌ MongoDB failed to start within ${timeout} seconds${NC}"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo -n "."
done
echo ""
echo -e "${GREEN}✅ MongoDB is ready${NC}"

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
timeout=60
elapsed=0
while ! curl -f http://localhost:8000/health/live > /dev/null 2>&1; do
    if [ $elapsed -ge $timeout ]; then
        echo -e "${RED}❌ Backend failed to start within ${timeout} seconds${NC}"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo -n "."
done
echo ""
echo -e "${GREEN}✅ Backend is ready${NC}"
echo ""

# Step 2: Get baseline connection count
echo -e "${YELLOW}Step 2: Getting baseline connection count...${NC}"
sleep 5  # Wait for initial connections to stabilize
BASELINE=$(get_connection_count)
echo -e "${GREEN}Baseline connections: ${BASELINE}${NC}"
echo ""

# Step 3: Test health endpoint (should use shared instance)
echo -e "${YELLOW}Step 3: Testing health endpoint (should reuse shared instance)...${NC}"
for i in {1..5}; do
    curl -s http://localhost:8000/health > /dev/null
    sleep 1
done
HEALTH_CONNECTIONS=$(get_connection_count)
echo -e "${GREEN}Connections after health checks: ${HEALTH_CONNECTIONS}${NC}"
if [ "$HEALTH_CONNECTIONS" -le "$((BASELINE + 2))" ]; then
    echo -e "${GREEN}✅ Connection count stable (health checker reusing shared instance)${NC}"
else
    echo -e "${YELLOW}⚠️  Connection count increased (may indicate health checker creating new instances)${NC}"
fi
echo ""

# Step 4: Test webhook endpoint (should use shared instance)
echo -e "${YELLOW}Step 4: Testing webhook health endpoint (should reuse shared instance)...${NC}"
for i in {1..5}; do
    curl -s http://localhost:8000/api/v1/sync/health > /dev/null
    sleep 1
done
WEBHOOK_CONNECTIONS=$(get_connection_count)
echo -e "${GREEN}Connections after webhook health checks: ${WEBHOOK_CONNECTIONS}${NC}"
if [ "$WEBHOOK_CONNECTIONS" -le "$((BASELINE + 2))" ]; then
    echo -e "${GREEN}✅ Connection count stable (webhook endpoints reusing shared instance)${NC}"
else
    echo -e "${YELLOW}⚠️  Connection count increased (may indicate webhook endpoints creating new instances)${NC}"
fi
echo ""

# Step 5: Monitor connections during application usage
echo -e "${YELLOW}Step 5: Monitoring connections for 30 seconds...${NC}"
echo "Connection count over time:"
for i in {1..6}; do
    count=$(get_connection_count)
    echo "  ${i}0s: ${count} connections"
    sleep 5
done
FINAL_CONNECTIONS=$(get_connection_count)
echo ""

# Step 6: Check backend logs for connection pool messages
echo -e "${YELLOW}Step 6: Checking backend logs for connection pool initialization...${NC}"
if docker logs $BACKEND_CONTAINER 2>&1 | grep -q "Shared MongoDB client created"; then
    echo -e "${GREEN}✅ Shared MongoDB client created${NC}"
else
    echo -e "${YELLOW}⚠️  Shared MongoDB client message not found in logs${NC}"
fi

if docker logs $BACKEND_CONTAINER 2>&1 | grep -q "using shared connection pool"; then
    echo -e "${GREEN}✅ VectorStoreManager using shared connection pool${NC}"
else
    echo -e "${YELLOW}⚠️  Shared connection pool message not found in logs${NC}"
fi

if docker logs $BACKEND_CONTAINER 2>&1 | grep -q "Global RAG pipeline instance set"; then
    echo -e "${GREEN}✅ Global RAG pipeline instance set for payload sync${NC}"
else
    echo -e "${YELLOW}⚠️  Global RAG pipeline setup message not found in logs${NC}"
fi

if docker logs $BACKEND_CONTAINER 2>&1 | grep -q "Health checker initialized with global VectorStoreManager"; then
    echo -e "${GREEN}✅ Health checker using global VectorStoreManager${NC}"
else
    echo -e "${YELLOW}⚠️  Health checker setup message not found in logs${NC}"
fi
echo ""

# Step 7: Summary
echo -e "${YELLOW}Step 7: Test Summary${NC}"
echo "========================================"
echo "Baseline connections:        ${BASELINE}"
echo "After health checks:         ${HEALTH_CONNECTIONS}"
echo "After webhook checks:        ${WEBHOOK_CONNECTIONS}"
echo "Final connections:           ${FINAL_CONNECTIONS}"
echo ""

# Calculate connection increase
INCREASE=$((FINAL_CONNECTIONS - BASELINE))
if [ "$INCREASE" -le 5 ]; then
    echo -e "${GREEN}✅ Connection count increase is minimal (${INCREASE} connections)${NC}"
    echo -e "${GREEN}   This indicates connection pool sharing is working correctly${NC}"
elif [ "$INCREASE" -le 10 ]; then
    echo -e "${YELLOW}⚠️  Connection count increased moderately (${INCREASE} connections)${NC}"
    echo -e "${YELLOW}   This may be normal, but monitor for connection leaks${NC}"
else
    echo -e "${RED}❌ Connection count increased significantly (${INCREASE} connections)${NC}"
    echo -e "${RED}   This may indicate connection leaks still exist${NC}"
fi
echo ""

# Step 8: Get detailed connection info
echo -e "${YELLOW}Step 8: Detailed connection information${NC}"
get_connection_details
echo ""

# Step 9: Test shutdown cleanup
echo -e "${YELLOW}Step 9: Testing shutdown cleanup...${NC}"
echo "Stopping backend container..."
docker stop $BACKEND_CONTAINER
sleep 5
SHUTDOWN_CONNECTIONS=$(get_connection_count)
echo -e "${GREEN}Connections after backend shutdown: ${SHUTDOWN_CONNECTIONS}${NC}"

if [ "$SHUTDOWN_CONNECTIONS" -lt "$FINAL_CONNECTIONS" ]; then
    echo -e "${GREEN}✅ Connections decreased after shutdown (cleanup working)${NC}"
else
    echo -e "${YELLOW}⚠️  Connections did not decrease significantly after shutdown${NC}"
fi

echo "Restarting backend..."
docker start $BACKEND_CONTAINER
sleep 10
echo -e "${GREEN}✅ Backend restarted${NC}"
echo ""

echo -e "${GREEN}✅ Testing complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Monitor MongoDB logs: docker logs -f $MONGO_CONTAINER"
echo "2. Monitor backend logs: docker logs -f $BACKEND_CONTAINER"
echo "3. Check connection count periodically: docker exec $MONGO_CONTAINER mongosh --quiet --eval 'db.serverStatus().connections.current'"
echo "4. Test with actual webhook payloads to verify connection stability"

