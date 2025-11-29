#!/bin/bash
# Test script to verify Prometheus and Grafana ports are bound to localhost only
# and are accessible locally but not from external interfaces

set -e

echo "🔒 Testing Monitoring Port Security (CRIT-NEW-1)"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo "1️⃣  Checking if services are running..."
PROMETHEUS_RUNNING=$(docker ps --filter "name=litecoin-prometheus" --format "{{.Names}}" 2>/dev/null | grep -q "litecoin-prometheus" && echo "yes" || echo "no")
GRAFANA_RUNNING=$(docker ps --filter "name=litecoin-grafana" --format "{{.Names}}" 2>/dev/null | grep -q "litecoin-grafana" && echo "yes" || echo "no")

if [ "$PROMETHEUS_RUNNING" != "yes" ] || [ "$GRAFANA_RUNNING" != "yes" ]; then
    echo -e "${RED}❌ Services are not running!${NC}"
    echo "   Please start services first with: ./scripts/run-prod.sh"
    exit 1
fi

echo -e "${GREEN}✅ Services are running${NC}"
echo ""

# Check port bindings
echo "2️⃣  Checking port bindings..."
PROMETHEUS_PORTS=$(docker port litecoin-prometheus 2>/dev/null || echo "")
GRAFANA_PORTS=$(docker port litecoin-grafana 2>/dev/null || echo "")

if [ -z "$PROMETHEUS_PORTS" ]; then
    echo -e "${RED}❌ Prometheus has no port mappings (this is correct for security)${NC}"
    echo "   However, you won't be able to access it via localhost"
    echo "   Consider binding to 127.0.0.1:9090:9090 for local access"
else
    echo "   Prometheus port mapping: $PROMETHEUS_PORTS"
    if echo "$PROMETHEUS_PORTS" | grep -q "127.0.0.1"; then
        echo -e "${GREEN}   ✅ Prometheus is bound to localhost only (secure)${NC}"
    elif echo "$PROMETHEUS_PORTS" | grep -q "0.0.0.0"; then
        echo -e "${RED}   ❌ Prometheus is bound to 0.0.0.0 (PUBLICLY EXPOSED - INSECURE!)${NC}"
    fi
fi

if [ -z "$GRAFANA_PORTS" ]; then
    echo -e "${RED}❌ Grafana has no port mappings (this is correct for security)${NC}"
    echo "   However, you won't be able to access it via localhost"
    echo "   Consider binding to 127.0.0.1:3002:3000 for local access"
else
    echo "   Grafana port mapping: $GRAFANA_PORTS"
    if echo "$GRAFANA_PORTS" | grep -q "127.0.0.1"; then
        echo -e "${GREEN}   ✅ Grafana is bound to localhost only (secure)${NC}"
    elif echo "$GRAFANA_PORTS" | grep -q "0.0.0.0"; then
        echo -e "${RED}   ❌ Grafana is bound to 0.0.0.0 (PUBLICLY EXPOSED - INSECURE!)${NC}"
    fi
fi
echo ""

# Test localhost access
echo "3️⃣  Testing localhost access..."

# Test Prometheus
echo -n "   Testing Prometheus (localhost:9090)... "
if curl -s -f -m 5 http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Accessible${NC}"
    PROMETHEUS_ACCESSIBLE=true
else
    echo -e "${YELLOW}⚠️  Not accessible (may be expected if ports are not bound)${NC}"
    PROMETHEUS_ACCESSIBLE=false
fi

# Test Grafana
echo -n "   Testing Grafana (localhost:3002)... "
if curl -s -f -m 5 http://localhost:3002/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Accessible${NC}"
    GRAFANA_ACCESSIBLE=true
else
    echo -e "${YELLOW}⚠️  Not accessible (may be expected if ports are not bound)${NC}"
    GRAFANA_ACCESSIBLE=false
fi
echo ""

# Test that ports are NOT bound to 0.0.0.0
echo "4️⃣  Verifying ports are NOT publicly exposed..."
echo "   Checking if ports are listening on all interfaces (0.0.0.0)..."

# Check using netstat or ss
if command -v ss > /dev/null 2>&1; then
    PROMETHEUS_PUBLIC=$(ss -tlnp 2>/dev/null | grep ":9090" | grep -q "0.0.0.0" && echo "yes" || echo "no")
    GRAFANA_PUBLIC=$(ss -tlnp 2>/dev/null | grep ":3002" | grep -q "0.0.0.0" && echo "yes" || echo "no")
elif command -v netstat > /dev/null 2>&1; then
    PROMETHEUS_PUBLIC=$(netstat -tlnp 2>/dev/null | grep ":9090" | grep -q "0.0.0.0" && echo "yes" || echo "no")
    GRAFANA_PUBLIC=$(netstat -tlnp 2>/dev/null | grep ":3002" | grep -q "0.0.0.0" && echo "yes" || echo "no")
else
    PROMETHEUS_PUBLIC="unknown"
    GRAFANA_PUBLIC="unknown"
    echo -e "${YELLOW}   ⚠️  Cannot check (netstat/ss not available)${NC}"
fi

if [ "$PROMETHEUS_PUBLIC" = "yes" ]; then
    echo -e "${RED}   ❌ Prometheus port 9090 is listening on 0.0.0.0 (PUBLICLY EXPOSED!)${NC}"
elif [ "$PROMETHEUS_PUBLIC" = "no" ]; then
    echo -e "${GREEN}   ✅ Prometheus port 9090 is NOT listening on 0.0.0.0 (secure)${NC}"
fi

if [ "$GRAFANA_PUBLIC" = "yes" ]; then
    echo -e "${RED}   ❌ Grafana port 3002 is listening on 0.0.0.0 (PUBLICLY EXPOSED!)${NC}"
elif [ "$GRAFANA_PUBLIC" = "no" ]; then
    echo -e "${GREEN}   ✅ Grafana port 3002 is NOT listening on 0.0.0.0 (secure)${NC}"
fi
echo ""

# Summary
echo "📊 Test Summary"
echo "==============="
if [ "$PROMETHEUS_ACCESSIBLE" = "true" ] && [ "$GRAFANA_ACCESSIBLE" = "true" ]; then
    if [ "$PROMETHEUS_PUBLIC" != "yes" ] && [ "$GRAFANA_PUBLIC" != "yes" ]; then
        echo -e "${GREEN}✅ PASS: Services are accessible locally and NOT publicly exposed${NC}"
        echo ""
        echo "   You can access:"
        echo "   - Prometheus: http://localhost:9090"
        echo "   - Grafana: http://localhost:3002"
        echo ""
        echo "   Security: Ports are bound to localhost only (127.0.0.1)"
        exit 0
    else
        echo -e "${RED}❌ FAIL: Services are publicly exposed!${NC}"
        exit 1
    fi
elif [ "$PROMETHEUS_ACCESSIBLE" = "false" ] && [ "$GRAFANA_ACCESSIBLE" = "false" ]; then
    echo -e "${YELLOW}⚠️  Services are not accessible via localhost${NC}"
    echo ""
    echo "   This may be because:"
    echo "   1. Ports are not bound (completely removed)"
    echo "   2. Services are not fully started yet"
    echo ""
    echo "   If you need local access, ensure ports are bound to 127.0.0.1"
    exit 0
else
    echo -e "${YELLOW}⚠️  Mixed results - check individual services${NC}"
    exit 1
fi

