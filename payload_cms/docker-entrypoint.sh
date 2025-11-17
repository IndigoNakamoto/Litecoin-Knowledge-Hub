#!/bin/sh
set -e

# Fix permissions for .next directory if it exists (from named volume)
# Aggressively clean and fix permissions before Next.js starts
if [ -d "/app/.next" ]; then
    # Remove problematic subdirectories that often cause permission issues
    rm -rf /app/.next/server 2>/dev/null || true
    rm -rf /app/.next/types 2>/dev/null || true
    rm -rf /app/.next/cache 2>/dev/null || true
    
    # Use find to remove any files that can't be modified
    # This handles cases where files have restrictive permissions
    find /app/.next -type f ! -perm -u+w -delete 2>/dev/null || true
    find /app/.next -type d ! -perm -u+w -exec chmod u+w {} \; 2>/dev/null || true
    
    # Fix permissions on remaining files and directories
    chmod -R 777 /app/.next 2>/dev/null || true
    chown -R node:node /app/.next 2>/dev/null || true
fi

# Ensure .next directory exists with proper permissions
mkdir -p /app/.next
chmod -R 777 /app/.next 2>/dev/null || true
chown -R node:node /app/.next 2>/dev/null || true

# Switch to node user and execute the command
# Ensure PATH includes /usr/local/bin where pnpm is installed
exec su-exec node sh -c "export PATH=\"/usr/local/bin:\$PATH\" && exec \"\$@\"" -- "$@"

