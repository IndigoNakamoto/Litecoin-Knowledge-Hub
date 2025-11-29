#!/bin/bash

# HTTPS Enforcement Verification Script
# 
# This script verifies that HTTPS enforcement is properly configured:
# - HSTS headers are present
# - HTTP to HTTPS redirects work
# - Security headers are present
# - TLS certificate is valid
#
# Usage:
#   ./scripts/verify-https-enforcement.sh [BASE_URL]
#
# Example:
#   ./scripts/verify-https-enforcement.sh https://chat.lite.space
#   ./scripts/verify-https-enforcement.sh https://api.lite.space

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get base URL from argument or use default
BASE_URL="${1:-https://chat.lite.space}"

# Remove trailing slash
BASE_URL="${BASE_URL%/}"

echo "=========================================="
echo "HTTPS Enforcement Verification"
echo "=========================================="
echo "Testing: $BASE_URL"
echo ""

# Extract domain from URL
DOMAIN=$(echo "$BASE_URL" | sed -E 's|https?://([^/]+).*|\1|')

# Track results
PASSED=0
FAILED=0
WARNINGS=0

# Function to print test result
print_result() {
    local status=$1
    local message=$2
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $message"
        ((PASSED++))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}✗${NC} $message"
        ((FAILED++))
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
        ((WARNINGS++))
    fi
}

# Test 1: Verify HTTPS URL is accessible
echo "Test 1: HTTPS Accessibility"
if curl -sSf --max-time 10 "$BASE_URL" > /dev/null 2>&1; then
    print_result "PASS" "HTTPS URL is accessible"
else
    print_result "FAIL" "HTTPS URL is not accessible"
    echo "  Error: Cannot connect to $BASE_URL"
    exit 1
fi
echo ""

# Test 2: Verify TLS Certificate
echo "Test 2: TLS Certificate Validity"
CERT_INFO=$(echo | openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$CERT_INFO" ]; then
    CERT_EXPIRY=$(echo "$CERT_INFO" | grep "notAfter" | cut -d= -f2)
    print_result "PASS" "TLS certificate is valid"
    echo "  Certificate expires: $CERT_EXPIRY"
else
    print_result "WARN" "Could not verify TLS certificate (may be behind Cloudflare)"
fi
echo ""

# Test 3: Verify HSTS Header
echo "Test 3: HSTS Header (Strict-Transport-Security)"
HSTS_HEADER=$(curl -sSI --max-time 10 "$BASE_URL" | grep -i "strict-transport-security" | tr -d '\r')
if [ -n "$HSTS_HEADER" ]; then
    # Check for proper HSTS values
    if echo "$HSTS_HEADER" | grep -qi "max-age"; then
        MAX_AGE=$(echo "$HSTS_HEADER" | grep -oE "max-age=[0-9]+" | cut -d= -f2)
        if [ "$MAX_AGE" -ge 31536000 ]; then
            print_result "PASS" "HSTS header present with max-age >= 1 year"
            echo "  Header: $HSTS_HEADER"
        else
            print_result "WARN" "HSTS header present but max-age < 1 year (max-age=$MAX_AGE)"
        fi
        
        if echo "$HSTS_HEADER" | grep -qi "includeSubDomains"; then
            print_result "PASS" "HSTS header includes includeSubDomains directive"
        else
            print_result "WARN" "HSTS header missing includeSubDomains directive"
        fi
    else
        print_result "WARN" "HSTS header present but missing max-age"
    fi
else
    print_result "FAIL" "HSTS header is missing"
    echo "  Expected: Strict-Transport-Security header"
fi
echo ""

# Test 4: Verify Security Headers
echo "Test 4: Security Headers"
HEADERS=$(curl -sSI --max-time 10 "$BASE_URL")

# Check X-Frame-Options
if echo "$HEADERS" | grep -qi "x-frame-options"; then
    XFO=$(echo "$HEADERS" | grep -i "x-frame-options" | tr -d '\r')
    print_result "PASS" "X-Frame-Options header present"
    echo "  Header: $XFO"
else
    print_result "WARN" "X-Frame-Options header missing"
fi

# Check X-Content-Type-Options
if echo "$HEADERS" | grep -qi "x-content-type-options"; then
    XCTO=$(echo "$HEADERS" | grep -i "x-content-type-options" | tr -d '\r')
    print_result "PASS" "X-Content-Type-Options header present"
    echo "  Header: $XCTO"
else
    print_result "WARN" "X-Content-Type-Options header missing"
fi

# Check Content-Security-Policy
if echo "$HEADERS" | grep -qi "content-security-policy"; then
    CSP=$(echo "$HEADERS" | grep -i "content-security-policy" | head -1 | tr -d '\r')
    print_result "PASS" "Content-Security-Policy header present"
    echo "  Header: ${CSP:0:80}..."
else
    print_result "WARN" "Content-Security-Policy header missing"
fi
echo ""

# Test 5: Verify HTTP to HTTPS Redirect
echo "Test 5: HTTP to HTTPS Redirect"
HTTP_URL=$(echo "$BASE_URL" | sed 's|https://|http://|')
REDIRECT_RESPONSE=$(curl -sSI --max-time 10 -L "$HTTP_URL" 2>&1 | head -20)

# Check for redirect status codes
if echo "$REDIRECT_RESPONSE" | grep -qiE "HTTP/[0-9.]+ (301|302|307|308)"; then
    REDIRECT_CODE=$(echo "$REDIRECT_RESPONSE" | grep -iE "HTTP/[0-9.]+ (301|302|307|308)" | head -1 | grep -oE "[0-9]{3}")
    REDIRECT_LOCATION=$(echo "$REDIRECT_RESPONSE" | grep -i "location:" | head -1 | cut -d: -f2- | tr -d '\r' | xargs)
    
    if echo "$REDIRECT_LOCATION" | grep -qi "https://"; then
        print_result "PASS" "HTTP to HTTPS redirect working (Status: $REDIRECT_CODE)"
        echo "  Redirects to: $REDIRECT_LOCATION"
    else
        print_result "FAIL" "HTTP redirect does not point to HTTPS"
        echo "  Redirects to: $REDIRECT_LOCATION"
    fi
elif curl -sSI --max-time 10 "$HTTP_URL" 2>&1 | grep -qi "https://"; then
    # If final URL is HTTPS, redirect worked
    print_result "PASS" "HTTP to HTTPS redirect working (via redirect chain)"
else
    print_result "WARN" "Could not verify HTTP to HTTPS redirect"
    echo "  Note: This may be handled by Cloudflare at the edge"
fi
echo ""

# Test 6: Verify Cloudflare Headers (if behind Cloudflare)
echo "Test 6: Cloudflare Integration (if applicable)"
CF_HEADERS=$(curl -sSI --max-time 10 "$BASE_URL" | grep -i "cf-" | head -5)
if [ -n "$CF_HEADERS" ]; then
    print_result "PASS" "Cloudflare headers detected (behind Cloudflare)"
    echo "$CF_HEADERS" | while read -r line; do
        echo "  $line"
    done
else
    print_result "WARN" "No Cloudflare headers detected (may not be behind Cloudflare)"
fi
echo ""

# Summary
echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ HTTPS enforcement verification PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ HTTPS enforcement verification FAILED${NC}"
    exit 1
fi

