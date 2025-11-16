#!/bin/sh
set -e

# Fix permissions for .next directory if it exists (from named volume)
# Use chmod first to ensure write permissions, then chown
if [ -d "/app/.next" ]; then
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

