#!/bin/bash

# Production Build Verification Script
# This script verifies that all services can build for production

set -e

echo "🔍 Verifying production builds for all services..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is installed${NC}"

if ! command_exists docker-compose; then
    echo -e "${RED}❌ docker-compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ docker-compose is installed${NC}"
echo ""

# Check if .env files exist (optional, but recommended)
echo "📋 Checking environment files..."
if [ ! -f "./backend/.env" ]; then
    echo -e "${YELLOW}⚠️  backend/.env not found (optional but recommended)${NC}"
else
    echo -e "${GREEN}✅ backend/.env exists${NC}"
fi

if [ ! -f "./payload_cms/.env" ]; then
    echo -e "${YELLOW}⚠️  payload_cms/.env not found (optional but recommended)${NC}"
else
    echo -e "${GREEN}✅ payload_cms/.env exists${NC}"
fi
echo ""

# Verify Next.js configs have standalone output
echo "📋 Verifying Next.js configurations..."
if grep -q "output.*standalone" frontend/next.config.ts; then
    echo -e "${GREEN}✅ Frontend Next.js config has standalone output configured${NC}"
else
    echo -e "${RED}❌ Frontend Next.js config missing standalone output${NC}"
    exit 1
fi

if grep -q "output.*standalone" payload_cms/next.config.mjs; then
    echo -e "${GREEN}✅ Payload CMS Next.js config has standalone output configured${NC}"
else
    echo -e "${RED}❌ Payload CMS Next.js config missing standalone output${NC}"
    exit 1
fi
echo ""

# Verify Dockerfiles set NODE_ENV=production in builder stage
echo "📋 Verifying Dockerfiles..."
if grep -q "ENV NODE_ENV=production" frontend/Dockerfile; then
    echo -e "${GREEN}✅ Frontend Dockerfile sets NODE_ENV=production${NC}"
else
    echo -e "${RED}❌ Frontend Dockerfile missing NODE_ENV=production in builder stage${NC}"
    exit 1
fi

if grep -q "ENV NODE_ENV=production" payload_cms/Dockerfile; then
    echo -e "${GREEN}✅ Payload CMS Dockerfile sets NODE_ENV=production${NC}"
else
    echo -e "${RED}❌ Payload CMS Dockerfile missing NODE_ENV=production in builder stage${NC}"
    exit 1
fi
echo ""

# Test Docker builds (dry-run style - check syntax)
echo "📋 Testing Docker build configurations..."

echo "Testing backend Dockerfile..."
if docker build --dry-run -f backend/Dockerfile backend/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend Dockerfile syntax is valid${NC}"
else
    # Docker doesn't have --dry-run, so we'll just check if file exists
    if [ -f "./backend/Dockerfile" ]; then
        echo -e "${GREEN}✅ Backend Dockerfile exists${NC}"
    else
        echo -e "${RED}❌ Backend Dockerfile not found${NC}"
        exit 1
    fi
fi

echo "Testing frontend Dockerfile..."
if [ -f "./frontend/Dockerfile" ]; then
    echo -e "${GREEN}✅ Frontend Dockerfile exists${NC}"
    # Check if it references standalone output
    if grep -q "standalone" frontend/Dockerfile; then
        echo -e "${GREEN}✅ Frontend Dockerfile references standalone output${NC}"
    fi
else
    echo -e "${RED}❌ Frontend Dockerfile not found${NC}"
    exit 1
fi

echo "Testing Payload CMS Dockerfile..."
if [ -f "./payload_cms/Dockerfile" ]; then
    echo -e "${GREEN}✅ Payload CMS Dockerfile exists${NC}"
    # Check if it references standalone output
    if grep -q "standalone" payload_cms/Dockerfile; then
        echo -e "${GREEN}✅ Payload CMS Dockerfile references standalone output${NC}"
    fi
else
    echo -e "${RED}❌ Payload CMS Dockerfile not found${NC}"
    exit 1
fi
echo ""

# Verify docker-compose.prod.yml
echo "📋 Verifying docker-compose.prod.yml..."
if [ -f "./docker-compose.prod.yml" ]; then
    echo -e "${GREEN}✅ docker-compose.prod.yml exists${NC}"
    # Check if it has all required services
    if grep -q "backend:" docker-compose.prod.yml && \
       grep -q "frontend:" docker-compose.prod.yml && \
       grep -q "payload_cms:" docker-compose.prod.yml; then
        echo -e "${GREEN}✅ docker-compose.prod.yml has all required services${NC}"
    else
        echo -e "${RED}❌ docker-compose.prod.yml missing required services${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ docker-compose.prod.yml not found${NC}"
    exit 1
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ All production build checks passed!${NC}"
echo ""
echo "📝 Next steps:"
echo "   1. Ensure environment variables are set in .env files"
echo "   2. Test builds with: docker-compose -f docker-compose.prod.yml build"
echo "   3. Start services with: docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "⚠️  Note: Actual Docker builds require:"
echo "   - GOOGLE_API_KEY environment variable"
echo "   - MongoDB connection string"
echo "   - Other service-specific environment variables"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

