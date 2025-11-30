#!/bin/bash
# Script to clear or update Redis settings for testing
# Usage: ./scripts/clear-redis-settings.sh [clear|show]

set -e

REDIS_CONTAINER="${REDIS_CONTAINER:-litecoin-redis-dev}"
SETTINGS_KEY="admin:settings:abuse_prevention"

ACTION="${1:-show}"

echo "🔧 Redis Settings Manager"
echo "========================="
echo ""
echo "Redis Container: $REDIS_CONTAINER"
echo "Settings Key: $SETTINGS_KEY"
echo ""

# Check if Redis container is running
if ! docker ps --format "{{.Names}}" | grep -q "^${REDIS_CONTAINER}$"; then
    echo "❌ Error: Redis container '$REDIS_CONTAINER' is not running"
    echo "   Start it with: ./scripts/run-dev.sh"
    exit 1
fi

if [ "$ACTION" = "clear" ]; then
    echo "🗑️  Clearing settings from Redis..."
    docker exec "$REDIS_CONTAINER" redis-cli DEL "$SETTINGS_KEY"
    echo "✅ Settings cleared! Backend will now use environment variables."
    echo ""
    echo "💡 Restart your backend to pick up environment variables:"
    echo "   docker restart litecoin-backend"
    echo "   (or restart with: ./scripts/run-dev.sh)"
    
elif [ "$ACTION" = "show" ]; then
    echo "📋 Current settings in Redis:"
    echo ""
    SETTINGS=$(docker exec "$REDIS_CONTAINER" redis-cli GET "$SETTINGS_KEY" 2>/dev/null || echo "")
    
    if [ -z "$SETTINGS" ] || [ "$SETTINGS" = "(nil)" ]; then
        echo "   (No settings found - backend will use environment variables)"
    else
        echo "$SETTINGS" | python3 -m json.tool 2>/dev/null || echo "$SETTINGS"
        echo ""
        echo "💡 To clear these settings, run:"
        echo "   ./scripts/clear-redis-settings.sh clear"
    fi
    
elif [ "$ACTION" = "set" ]; then
    if [ -z "$2" ] || [ -z "$3" ]; then
        echo "❌ Error: Usage: ./scripts/clear-redis-settings.sh set <key> <value>"
        echo ""
        echo "Example:"
        echo "   ./scripts/clear-redis-settings.sh set enable_challenge_response false"
        exit 1
    fi
    
    SETTING_KEY="$2"
    SETTING_VALUE="$3"
    
    echo "✏️  Updating setting: $SETTING_KEY = $SETTING_VALUE"
    
    # Get current settings
    CURRENT=$(docker exec "$REDIS_CONTAINER" redis-cli GET "$SETTINGS_KEY" 2>/dev/null || echo "{}")
    
    if [ -z "$CURRENT" ] || [ "$CURRENT" = "(nil)" ]; then
        CURRENT="{}"
    fi
    
    # Update the setting using Python
    UPDATED=$(echo "$CURRENT" | python3 -c "
import sys, json
settings = json.load(sys.stdin) if sys.stdin.read(1) else {}
settings['$SETTING_KEY'] = '$SETTING_VALUE'
print(json.dumps(settings))
")
    
    # Save back to Redis
    docker exec -i "$REDIS_CONTAINER" redis-cli SET "$SETTINGS_KEY" "$UPDATED" > /dev/null
    
    echo "✅ Setting updated!"
    echo ""
    echo "💡 Restart your backend to pick up the change:"
    echo "   docker restart litecoin-backend"
    
else
    echo "❌ Unknown action: $ACTION"
    echo ""
    echo "Usage:"
    echo "   ./scripts/clear-redis-settings.sh [show|clear|set <key> <value>]"
    echo ""
    echo "Examples:"
    echo "   ./scripts/clear-redis-settings.sh show"
    echo "   ./scripts/clear-redis-settings.sh clear"
    echo "   ./scripts/clear-redis-settings.sh set enable_challenge_response false"
    exit 1
fi

echo ""

