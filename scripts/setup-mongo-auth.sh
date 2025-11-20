#!/bin/bash

# MongoDB Authentication Setup Script
# This script helps you create MongoDB users and enable authentication

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 MongoDB Authentication Setup${NC}"
echo "=================================="
echo ""

# Determine which compose file and container to use
if docker ps --format '{{.Names}}' | grep -q "^litecoin-mongodb$"; then
    COMPOSE_FILE="docker-compose.prod.yml"
    MONGO_CONTAINER="litecoin-mongodb"
    ENV_FILE=".env.docker.prod"
elif docker ps --format '{{.Names}}' | grep -q "^litecoin-mongodb-dev$"; then
    COMPOSE_FILE="docker-compose.dev.yml"
    MONGO_CONTAINER="litecoin-mongodb-dev"
    ENV_FILE=".env.docker.dev"
elif docker ps --format '{{.Names}}' | grep -q "^litecoin-mongodb-prod-local$"; then
    COMPOSE_FILE="docker-compose.prod-local.yml"
    MONGO_CONTAINER="litecoin-mongodb-prod-local"
    ENV_FILE=".env.prod-local"
else
    echo -e "${RED}❌ No MongoDB container found. Please start your services first.${NC}"
    exit 1
fi

echo -e "${GREEN}Using: ${COMPOSE_FILE}${NC}"
echo -e "${GREEN}Container: ${MONGO_CONTAINER}${NC}"
echo -e "${GREEN}Env file: ${ENV_FILE}${NC}"
echo ""

# Check if MongoDB is running
if ! docker ps --format '{{.Names}}' | grep -q "^${MONGO_CONTAINER}$"; then
    echo -e "${RED}❌ MongoDB container ${MONGO_CONTAINER} is not running.${NC}"
    echo -e "${YELLOW}Starting services...${NC}"
    docker compose -f ${COMPOSE_FILE} up -d mongodb
    echo "Waiting for MongoDB to be ready..."
    sleep 5
fi

# Check if .env file exists
if [ ! -f "${ENV_FILE}" ]; then
    echo -e "${RED}❌ Environment file ${ENV_FILE} not found.${NC}"
    exit 1
fi

# Source the .env file to get passwords
set -a
source "${ENV_FILE}"
set +a

# Check if passwords are set
if [ -z "$MONGO_ROOT_PASSWORD" ] || [ -z "$MONGO_APP_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️  Passwords not found in ${ENV_FILE}${NC}"
    echo ""
    echo "Please add the following to ${ENV_FILE}:"
    echo ""
    echo "MONGO_ROOT_USERNAME=admin"
    echo "MONGO_ROOT_PASSWORD=<your-root-password>"
    echo "MONGO_APP_USERNAME=litecoin_app"
    echo "MONGO_APP_PASSWORD=<your-app-password>"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Passwords found in ${ENV_FILE}${NC}"
echo ""

# Check if MongoDB requires authentication
echo -e "${YELLOW}Checking MongoDB authentication status...${NC}"
AUTH_REQUIRED=$(docker exec ${MONGO_CONTAINER} mongosh --quiet --eval "db.adminCommand('getCmdLineOpts').parsed.security.authorization" 2>/dev/null || echo "undefined")

if [ "$AUTH_REQUIRED" = "enabled" ] || [ "$AUTH_REQUIRED" = "true" ]; then
    echo -e "${YELLOW}⚠️  MongoDB authentication is already enabled.${NC}"
    echo -e "${YELLOW}Attempting to create users with authentication...${NC}"
    AUTH_FLAGS="--username ${MONGO_ROOT_USERNAME:-admin} --password ${MONGO_ROOT_PASSWORD} --authenticationDatabase admin"
else
    echo -e "${GREEN}✓ MongoDB is running without authentication (good for creating users)${NC}"
    AUTH_FLAGS=""
fi

echo ""
echo -e "${BLUE}Creating MongoDB users...${NC}"
echo ""

# Run the user creation script
docker exec -i \
    -e MONGO_ROOT_USERNAME="${MONGO_ROOT_USERNAME:-admin}" \
    -e MONGO_ROOT_PASSWORD="${MONGO_ROOT_PASSWORD}" \
    -e MONGO_APP_USERNAME="${MONGO_APP_USERNAME:-litecoin_app}" \
    -e MONGO_APP_PASSWORD="${MONGO_APP_PASSWORD}" \
    ${MONGO_CONTAINER} mongosh ${AUTH_FLAGS} < scripts/create-mongo-users.js

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Users created successfully!${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. ✅ Users are created"
    echo "2. ✅ Passwords are set in ${ENV_FILE}"
    echo "3. ${YELLOW}Restart services to enable authentication:${NC}"
    echo "   docker compose -f ${COMPOSE_FILE} restart mongodb"
    echo ""
    echo -e "${GREEN}After restart, MongoDB will automatically enable authentication because passwords are set.${NC}"
else
    echo ""
    echo -e "${RED}❌ Failed to create users. Please check the error messages above.${NC}"
    exit 1
fi

