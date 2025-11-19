#!/bin/bash
# Script to refresh the suggested question cache via admin endpoint
# This script is designed to be run via cron job every 48 hours (every 2 days)

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load environment variables from backend/.env if it exists
if [ -f "$PROJECT_ROOT/backend/.env" ]; then
    set -a
    source "$PROJECT_ROOT/backend/.env"
    set +a
fi

# Get admin token from environment
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

if [ -z "$ADMIN_TOKEN" ]; then
    echo "ERROR: ADMIN_TOKEN environment variable is not set"
    echo "Please set ADMIN_TOKEN in backend/.env or export it in your environment"
    exit 1
fi

# Get backend URL (default to localhost for local cron, or use env var)
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# Log file location
LOG_FILE="${LOG_FILE:-/var/log/suggested-cache-refresh.log}"

# Create log directory if it doesn't exist
LOG_DIR=$(dirname "$LOG_FILE")
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR" 2>/dev/null || {
        # If we can't create the log directory, use a local log file
        LOG_FILE="$PROJECT_ROOT/suggested-cache-refresh.log"
    }
fi

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting suggested question cache refresh..."

# Make the API call
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BACKEND_URL/api/v1/admin/refresh-suggested-cache" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -m 300)  # 5 minute timeout

# Extract HTTP status code (last line)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
# Extract response body (all but last line)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    log "Cache refresh successful: $BODY"
    exit 0
else
    log "ERROR: Cache refresh failed with HTTP $HTTP_CODE"
    log "Response: $BODY"
    exit 1
fi

