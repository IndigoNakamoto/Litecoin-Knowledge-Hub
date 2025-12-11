#!/bin/bash

# End-to-end MongoDB backup + encryption helper for GitHub storage
# ----------------------------------------------------------------
# This script:
#   1. Runs scripts/backup-mongodb.sh to create a fresh dump of litecoin_rag_db + payload_cms
#   2. Runs scripts/archive-encrypt-mongodb-backup.sh to archive + encrypt the latest backup
#   3. Prints suggested git commands to stage and commit the encrypted artifact
#
# It does NOT automatically run git commit or git push; those remain manual.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "🧩 Step 1/2: Running MongoDB backup script..."
./scripts/backup-mongodb.sh

echo ""
echo "🧩 Step 2/2: Archiving and encrypting latest backup..."
./scripts/archive-encrypt-mongodb-backup.sh

ENCRYPTED_ROOT="$PROJECT_ROOT/encrypted-backups"
LATEST_ENCRYPTED=$(ls -1t "$ENCRYPTED_ROOT" 2>/dev/null | head -n 1 || true)

echo ""
if [ -z "$LATEST_ENCRYPTED" ]; then
  echo "⚠️  Could not find an encrypted backup in $ENCRYPTED_ROOT"
  echo "   Check the output above for errors."
  exit 1
fi

ENCRYPTED_PATH="encrypted-backups/$LATEST_ENCRYPTED"

echo "✅ Backup + encryption finished."
echo ""
echo "You can now commit the encrypted backup to your private GitHub repo:"
echo ""
echo "  cd $PROJECT_ROOT"
echo "  git add $ENCRYPTED_PATH"
echo "  git commit -m \"chore: mongo backup $LATEST_ENCRYPTED\""
echo "  git push"
echo ""
echo "💡 Tip: For disaster recovery, store your age/GPG private key in a secure password manager so"
echo "   another dev can decrypt and restore from these backups if needed."


