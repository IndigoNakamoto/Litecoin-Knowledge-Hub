#!/bin/bash

# Archive & Encrypt Latest MongoDB Backup
# --------------------------------------
# This script:
#   1. Finds the most recent backup directory under mongodb-migration-backup/backup-<TIMESTAMP>
#   2. Creates a tar.gz archive of that directory
#   3. Encrypts the archive using age (recommended) or GPG
#   4. Writes the encrypted archive into ./encrypted-backups/ for easy Git commits
#
# Requirements:
#   - A recent backup created by scripts/backup-mongodb.sh
#   - Either:
#       * age installed, with AGE_BACKUP_RECIPIENT set to an age recipient string
#         (e.g., age1... from your public key), or
#       * gpg installed, with MONGODB_BACKUP_GPG_RECIPIENT set to a GPG recipient
#         (key ID or email)
#
# This script does NOT push to Git; it only prepares the encrypted artifact.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

BACKUP_ROOT="$PROJECT_ROOT/mongodb-migration-backup"
ENCRYPTED_ROOT="$PROJECT_ROOT/encrypted-backups"

mkdir -p "$ENCRYPTED_ROOT"

cd "$BACKUP_ROOT"

LATEST_BACKUP_DIR=$(ls -1dt backup-* 2>/dev/null | head -n 1 || true)

if [ -z "$LATEST_BACKUP_DIR" ]; then
  echo "❌ No backup directories found under $BACKUP_ROOT"
  echo "   Run scripts/backup-mongodb.sh first."
  exit 1
fi

TIMESTAMP="${LATEST_BACKUP_DIR#backup-}"
ARCHIVE_NAME="mongodb-backup-${TIMESTAMP}.tar.gz"
ARCHIVE_PATH="$BACKUP_ROOT/$ARCHIVE_NAME"

echo "📦 Creating archive from latest backup: $LATEST_BACKUP_DIR"
tar -czf "$ARCHIVE_PATH" "$LATEST_BACKUP_DIR"
echo "   ✓ Created: $ARCHIVE_PATH"

ENCRYPTED_AGE_PATH="$ENCRYPTED_ROOT/${ARCHIVE_NAME}.age"
ENCRYPTED_GPG_PATH="$ENCRYPTED_ROOT/${ARCHIVE_NAME}.gpg"

if command -v age >/dev/null 2>&1 && [ -n "${AGE_BACKUP_RECIPIENT:-}" ]; then
  echo "🔐 Encrypting with age..."
  age -r "$AGE_BACKUP_RECIPIENT" -o "$ENCRYPTED_AGE_PATH" "$ARCHIVE_PATH"
  echo "   ✓ Encrypted (age): $ENCRYPTED_AGE_PATH"
elif command -v gpg >/dev/null 2>&1 && [ -n "${MONGODB_BACKUP_GPG_RECIPIENT:-}" ]; then
  echo "🔐 Encrypting with GPG..."
  gpg --output "$ENCRYPTED_GPG_PATH" --encrypt --recipient "$MONGODB_BACKUP_GPG_RECIPIENT" "$ARCHIVE_PATH"
  echo "   ✓ Encrypted (gpg): $ENCRYPTED_GPG_PATH"
else
  echo "⚠️  No encryption tool configured."
  echo "   Either:"
  echo "     - Install age and set AGE_BACKUP_RECIPIENT to your age public recipient, or"
  echo "     - Install gpg and set MONGODB_BACKUP_GPG_RECIPIENT to a GPG key (email or ID)."
  echo "   The unencrypted archive remains at:"
  echo "     $ARCHIVE_PATH"
  exit 1
fi

echo ""
echo "✅ Archive and encryption complete."
echo "   Latest encrypted backups are in: $ENCRYPTED_ROOT"



