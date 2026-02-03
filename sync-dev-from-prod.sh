#!/bin/bash
set -e

# Sync dev environment from production
# Usage: ./sync-dev-from-prod.sh
#
# Syncs database, media files, and optionally code from prod to dev.
# Uses DEV_HOST and PRODUCTION_HOST from .env

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_PATH="/opt/basal"

# Load hosts from .env
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "Error: .env file not found"
  exit 1
fi

DEV_HOST=$(grep -E '^DEV_HOST=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)
PROD_HOST=$(grep -E '^PRODUCTION_HOST=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)

if [ -z "$DEV_HOST" ] || [ -z "$PROD_HOST" ]; then
  echo "Error: DEV_HOST and PRODUCTION_HOST must be set in .env"
  exit 1
fi

DEV_SERVER="root@$DEV_HOST"
PROD_SERVER="root@$PROD_HOST"

echo "========================================"
echo "  Sync Dev from Production"
echo "========================================"
echo ""
echo "  Source (prod): $PROD_HOST"
echo "  Target (dev):  $DEV_HOST"
echo ""
echo "This will OVERWRITE the dev database and media files!"
echo ""
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Cancelled."
  exit 0
fi

# Ask about code sync
echo ""
read -p "Also sync code to prod's current commit? [y/N] " -n 1 -r
echo
SYNC_CODE=false
if [[ $REPLY =~ ^[Yy]$ ]]; then
  SYNC_CODE=true
fi

# Check SSH access
echo ""
echo "==> Checking SSH access..."
if ! ssh -q -o ConnectTimeout=5 "$PROD_SERVER" exit; then
  echo "Error: Cannot connect to prod server ($PROD_SERVER)"
  exit 1
fi
if ! ssh -q -o ConnectTimeout=5 "$DEV_SERVER" exit; then
  echo "Error: Cannot connect to dev server ($DEV_SERVER)"
  exit 1
fi
echo "    SSH access OK"

# Sync code if requested
if [ "$SYNC_CODE" = true ]; then
  echo ""
  echo "==> Getting prod's current git commit..."
  PROD_COMMIT=$(ssh "$PROD_SERVER" "cd $REMOTE_PATH && git rev-parse HEAD 2>/dev/null || echo 'none'")

  if [ "$PROD_COMMIT" != "none" ]; then
    echo "    Prod is at commit: $PROD_COMMIT"
  fi

  # Always sync via rsync (prod → local temp → dev) to avoid touching local code
  echo "==> Syncing code (prod → local → dev)..."
  TEMP_CODE="/tmp/basal-code-sync"
  rm -rf "$TEMP_CODE"
  mkdir -p "$TEMP_CODE"
  rsync -avz \
    --exclude='.env' \
    --exclude='.env2' \
    --exclude='media' \
    --exclude='staticfiles' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='*.egg-info' \
    --exclude='build' \
    --exclude='venv' \
    --exclude='.venv' \
    "$PROD_SERVER:$REMOTE_PATH/" "$TEMP_CODE/"
  rsync -avz --delete \
    --exclude='.env' \
    --exclude='.env2' \
    --exclude='media' \
    --exclude='staticfiles' \
    "$TEMP_CODE/" "$DEV_SERVER:$REMOTE_PATH/"
  rm -rf "$TEMP_CODE"

  echo "==> Rebuilding dev containers..."
  ssh "$DEV_SERVER" "cd $REMOTE_PATH && docker compose build && docker compose up -d"
fi

# Database sync
echo ""
echo "==> Dumping prod database..."
DUMP_FILE="/tmp/basal-prod-dump-$(date +%Y%m%d-%H%M%S).sql"
ssh "$PROD_SERVER" "cd $REMOTE_PATH && docker compose exec -T db pg_dump -U postgres basal" > "$DUMP_FILE"
DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "    Dump saved to $DUMP_FILE ($DUMP_SIZE)"

echo ""
echo "==> Stopping dev app (to release db connections)..."
ssh "$DEV_SERVER" "cd $REMOTE_PATH && docker compose stop app"

echo ""
echo "==> Restoring database to dev..."
# Drop and recreate database
ssh "$DEV_SERVER" "cd $REMOTE_PATH && docker compose exec -T db psql -U postgres -c 'DROP DATABASE IF EXISTS basal;'" || true
ssh "$DEV_SERVER" "cd $REMOTE_PATH && docker compose exec -T db psql -U postgres -c 'CREATE DATABASE basal;'"

# Restore dump
cat "$DUMP_FILE" | ssh "$DEV_SERVER" "cd $REMOTE_PATH && docker compose exec -T db psql -U postgres basal" > /dev/null
echo "    Database restored"

echo ""
echo "==> Starting dev app..."
ssh "$DEV_SERVER" "cd $REMOTE_PATH && docker compose start app"

# Media files sync (via local machine)
echo ""
echo "==> Syncing media files (prod → local → dev)..."
TEMP_MEDIA="/tmp/basal-media-sync"
rm -rf "$TEMP_MEDIA"
mkdir -p "$TEMP_MEDIA"
rsync -avz "$PROD_SERVER:$REMOTE_PATH/media/" "$TEMP_MEDIA/"
rsync -avz "$TEMP_MEDIA/" "$DEV_SERVER:$REMOTE_PATH/media/"
rm -rf "$TEMP_MEDIA"

# Run migrations (in case dev code is ahead)
if [ "$SYNC_CODE" = false ]; then
  echo ""
  echo "==> Running migrations on dev (in case local code is ahead)..."
  ssh "$DEV_SERVER" "cd $REMOTE_PATH && docker compose exec -T app python manage.py migrate" || true
fi

# Collect static
echo ""
echo "==> Collecting static files on dev..."
ssh "$DEV_SERVER" "cd $REMOTE_PATH && docker compose exec -T app python manage.py collectstatic --noinput" > /dev/null

# Cleanup
rm -f "$DUMP_FILE"

echo ""
echo "========================================"
echo "  Sync complete!"
echo "========================================"
echo ""
echo "Dev is now a copy of prod."
if [ "$SYNC_CODE" = true ]; then
  echo "Code synced from prod."
fi
