#!/bin/bash

# MongoDB Authentication Verification Script
# This script verifies that MongoDB authentication is properly configured

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 MongoDB Authentication Verification${NC}"
echo "======================================"
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
    echo ""
    echo "Start services with:"
    echo "  docker compose -f docker-compose.prod.yml up -d"
    exit 1
fi

echo -e "${GREEN}Using: ${COMPOSE_FILE}${NC}"
echo -e "${GREEN}Container: ${MONGO_CONTAINER}${NC}"
echo -e "${GREEN}Env file: ${ENV_FILE}${NC}"
echo ""

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
    echo "Authentication will not be enabled."
    echo ""
else
    echo -e "${GREEN}✓ Passwords found in ${ENV_FILE}${NC}"
fi

echo ""
echo -e "${BLUE}Checking MongoDB authentication status...${NC}"

# Check if MongoDB requires authentication
AUTH_STATUS=$(docker exec ${MONGO_CONTAINER} mongosh --quiet --eval "try { db.adminCommand('getCmdLineOpts').parsed.security.authorization } catch(e) { 'undefined' }" 2>/dev/null || echo "undefined")

if [ "$AUTH_STATUS" = "enabled" ] || [ "$AUTH_STATUS" = "true" ]; then
    echo -e "${GREEN}✓ MongoDB authentication is ENABLED${NC}"
    AUTH_ENABLED=true
elif [ -n "$MONGO_ROOT_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️  MongoDB authentication is NOT enabled, but passwords are set${NC}"
    echo -e "${YELLOW}   Authentication should be enabled. Restart MongoDB:${NC}"
    echo -e "${YELLOW}   docker compose -f ${COMPOSE_FILE} restart mongodb${NC}"
    AUTH_ENABLED=false
else
    echo -e "${YELLOW}⚠️  MongoDB authentication is NOT enabled (no passwords set)${NC}"
    AUTH_ENABLED=false
fi

echo ""

# Try to list users
echo -e "${BLUE}Checking MongoDB users...${NC}"

if [ "$AUTH_ENABLED" = "true" ] && [ -n "$MONGO_ROOT_PASSWORD" ]; then
    # Try with authentication
    USERS=$(docker exec ${MONGO_CONTAINER} mongosh --quiet \
        --username "${MONGO_ROOT_USERNAME:-admin}" \
        --password "${MONGO_ROOT_PASSWORD}" \
        --authenticationDatabase admin \
        --eval "db.getUsers()" 2>/dev/null || echo "ERROR")
else
    # Try without authentication
    USERS=$(docker exec ${MONGO_CONTAINER} mongosh --quiet \
        --eval "db.getUsers()" 2>/dev/null || echo "ERROR")
fi

if echo "$USERS" | grep -q "ERROR\|Error\|error"; then
    echo -e "${RED}❌ Failed to retrieve users${NC}"
    echo "$USERS"
else
    if echo "$USERS" | grep -q "litecoin_app\|admin"; then
        echo -e "${GREEN}✓ Users found:${NC}"
        echo "$USERS" | grep -E "user|roles" | head -10
    else
        echo -e "${YELLOW}⚠️  No application users found${NC}"
        echo "Users in database:"
        echo "$USERS"
    fi
fi

echo ""

# Check connection strings in .env file
echo -e "${BLUE}Checking connection strings in ${ENV_FILE}...${NC}"

if grep -q "MONGO_URI.*@mongodb.*authSource" "${ENV_FILE}" 2>/dev/null; then
    echo -e "${GREEN}✓ MONGO_URI includes authentication${NC}"
else
    echo -e "${YELLOW}⚠️  MONGO_URI may not include authentication${NC}"
    echo "   Should be: mongodb://litecoin_app:PASSWORD@mongodb:27017/litecoin_rag_db?authSource=litecoin_rag_db"
fi

if grep -q "DATABASE_URI.*@mongodb.*authSource" "${ENV_FILE}" 2>/dev/null; then
    echo -e "${GREEN}✓ DATABASE_URI includes authentication${NC}"
else
    echo -e "${YELLOW}⚠️  DATABASE_URI may not include authentication${NC}"
    echo "   Should be: mongodb://litecoin_app:PASSWORD@mongodb:27017/payload_cms?authSource=payload_cms"
fi

if grep -q "REDIS_URL.*@redis" "${ENV_FILE}" 2>/dev/null || grep -q "REDIS_PASSWORD" "${ENV_FILE}" 2>/dev/null; then
    echo -e "${GREEN}✓ Redis authentication configured${NC}"
else
    echo -e "${YELLOW}⚠️  Redis authentication may not be configured${NC}"
fi

echo ""

# Test connections
echo -e "${BLUE}Testing connections...${NC}"

# Test MongoDB connection
if [ "$AUTH_ENABLED" = "true" ] && [ -n "$MONGO_ROOT_PASSWORD" ]; then
    MONGO_TEST=$(docker exec ${MONGO_CONTAINER} mongosh --quiet \
        --username "${MONGO_ROOT_USERNAME:-admin}" \
        --password "${MONGO_ROOT_PASSWORD}" \
        --authenticationDatabase admin \
        --eval "db.adminCommand('ping')" 2>&1)
else
    MONGO_TEST=$(docker exec ${MONGO_CONTAINER} mongosh --quiet \
        --eval "db.adminCommand('ping')" 2>&1)
fi

if echo "$MONGO_TEST" | grep -q "ok.*1"; then
    echo -e "${GREEN}✓ MongoDB connection successful${NC}"
else
    echo -e "${RED}❌ MongoDB connection failed${NC}"
    echo "$MONGO_TEST"
fi

# Test Redis connection
if docker ps --format '{{.Names}}' | grep -q "^litecoin-redis"; then
    REDIS_CONTAINER=$(docker ps --format '{{.Names}}' | grep "^litecoin-redis" | head -1)
    if [ -n "$REDIS_PASSWORD" ]; then
        REDIS_TEST=$(docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD}" ping 2>&1)
    else
        REDIS_TEST=$(docker exec ${REDIS_CONTAINER} redis-cli ping 2>&1)
    fi
    
    if echo "$REDIS_TEST" | grep -q "PONG"; then
        echo -e "${GREEN}✓ Redis connection successful${NC}"
    elif echo "$REDIS_TEST" | grep -q "NOAUTH"; then
        echo -e "${YELLOW}⚠️  Redis requires authentication but password not provided${NC}"
    else
        echo -e "${RED}❌ Redis connection failed${NC}"
        echo "$REDIS_TEST"
    fi
fi

echo ""
echo -e "${BLUE}Summary:${NC}"
echo "=========="

if [ "$AUTH_ENABLED" = "true" ] && [ -n "$MONGO_ROOT_PASSWORD" ] && echo "$USERS" | grep -q "litecoin_app"; then
    echo -e "${GREEN}✅ MongoDB authentication is properly configured!${NC}"
    echo ""
    echo "Your setup looks good. Services should work with authentication enabled."
else
    echo -e "${YELLOW}⚠️  Setup may need attention:${NC}"
    echo ""
    if [ "$AUTH_ENABLED" != "true" ] && [ -n "$MONGO_ROOT_PASSWORD" ]; then
        echo "  - Restart MongoDB to enable authentication"
    fi
    if ! echo "$USERS" | grep -q "litecoin_app"; then
        echo "  - Run ./scripts/setup-mongo-auth.sh to create users"
    fi
    if ! grep -q "MONGO_URI.*@mongodb.*authSource" "${ENV_FILE}" 2>/dev/null; then
        echo "  - Update connection strings in ${ENV_FILE} to include credentials"
    fi
fi

echo ""

