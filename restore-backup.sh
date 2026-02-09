#!/bin/bash
set -e

# Restore a backup to dev or prod
# Usage:
#   ./restore-backup.sh --dev [backup_name]    # restore to dev
#   ./restore-backup.sh --prod [backup_name]   # restore to prod
#   ./restore-backup.sh --list                  # list available backups from S3
#
# If backup_name is omitted, lists available backups and prompts for selection.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_PATH="/opt/basal"

# Parse arguments
TARGET=""
BACKUP_NAME=""
LIST_ONLY=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --dev)  TARGET="dev"; shift ;;
    --prod) TARGET="prod"; shift ;;
    --list) LIST_ONLY=true; shift ;;
    *)      BACKUP_NAME="$1"; shift ;;
  esac
done

# Load .env
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "Error: .env file not found"
  exit 1
fi

DEV_HOST=$(grep -E '^DEV_HOST=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)
PROD_HOST=$(grep -E '^PRODUCTION_HOST=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)
S3_ACCESS_KEY=$(grep -E '^S3_ACCESS_KEY=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)
S3_SECRET_KEY=$(grep -E '^S3_SECRET_KEY=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)
S3_BUCKET_NAME=$(grep -E '^S3_BUCKET_NAME=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)
S3_ENDPOINT=$(grep -E '^S3_ENDPOINT=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)

# Helper: list backups from S3
list_backups() {
  echo "Fetching backups from S3..."
  echo ""

  # List all manifest.json files to get backup info
  manifests=$(AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
    aws s3 ls "s3://$S3_BUCKET_NAME/backups/" \
    --endpoint-url "$S3_ENDPOINT" \
    --recursive 2>/dev/null | grep "manifest.json" | sort -r)

  if [ -z "$manifests" ]; then
    # Fallback: list directories even without manifests
    echo "No manifests found. Listing backup directories:"
    AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
      aws s3 ls "s3://$S3_BUCKET_NAME/backups/" \
      --endpoint-url "$S3_ENDPOINT" 2>/dev/null | grep "PRE" | awk '{print $2}' | sed 's/\///'
    return
  fi

  # Download and display each manifest
  printf "%-28s %-14s %-10s %s\n" "BACKUP" "DATE" "BRANCH" "COMMIT"
  printf "%-28s %-14s %-10s %s\n" "------" "----" "------" "------"

  while IFS= read -r line; do
    key=$(echo "$line" | awk '{print $4}')
    backup_dir=$(echo "$key" | cut -d'/' -f2)

    manifest=$(AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
      aws s3 cp "s3://$S3_BUCKET_NAME/$key" - \
      --endpoint-url "$S3_ENDPOINT" 2>/dev/null)

    timestamp=$(echo "$manifest" | python3 -c "import sys,json; print(json.load(sys.stdin).get('timestamp','?')[:16])" 2>/dev/null || echo "?")
    branch=$(echo "$manifest" | python3 -c "import sys,json; print(json.load(sys.stdin).get('git_branch','?'))" 2>/dev/null || echo "?")
    commit=$(echo "$manifest" | python3 -c "import sys,json; print(json.load(sys.stdin).get('git_commit','?')[:12])" 2>/dev/null || echo "?")

    printf "%-28s %-14s %-10s %s\n" "$backup_dir" "$timestamp" "$branch" "$commit"
  done <<< "$manifests"
}

# List mode
if [ "$LIST_ONLY" = true ]; then
  list_backups
  exit 0
fi

# Validate target
if [ -z "$TARGET" ]; then
  echo "Usage: ./restore-backup.sh [--dev|--prod] [backup_name]"
  echo "       ./restore-backup.sh --list"
  exit 1
fi

# Set server based on target
if [ "$TARGET" = "prod" ]; then
  HOST="$PROD_HOST"
  if [ -z "$HOST" ]; then
    echo "Error: PRODUCTION_HOST not set in .env"
    exit 1
  fi
else
  HOST="$DEV_HOST"
  if [ -z "$HOST" ]; then
    echo "Error: DEV_HOST not set in .env"
    exit 1
  fi
fi
SERVER="root@$HOST"

# If no backup name, list and prompt
if [ -z "$BACKUP_NAME" ]; then
  list_backups
  echo ""
  read -p "Enter backup name to restore: " BACKUP_NAME
  if [ -z "$BACKUP_NAME" ]; then
    echo "No backup selected. Cancelled."
    exit 0
  fi
fi

# Normalize backup name
if [[ ! "$BACKUP_NAME" == backup_* ]]; then
  BACKUP_NAME="backup_$BACKUP_NAME"
fi

echo ""
echo "========================================"
echo "  Restore Backup"
echo "========================================"
echo ""
echo "  Backup:  $BACKUP_NAME"
echo "  Target:  $TARGET ($HOST)"
echo ""

# Download manifest
echo "==> Downloading manifest..."
MANIFEST=$(AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
  aws s3 cp "s3://$S3_BUCKET_NAME/backups/$BACKUP_NAME/manifest.json" - \
  --endpoint-url "$S3_ENDPOINT" 2>/dev/null || echo "")

if [ -n "$MANIFEST" ]; then
  BACKUP_COMMIT=$(echo "$MANIFEST" | python3 -c "import sys,json; print(json.load(sys.stdin).get('git_commit',''))" 2>/dev/null)
  BACKUP_BRANCH=$(echo "$MANIFEST" | python3 -c "import sys,json; print(json.load(sys.stdin).get('git_branch',''))" 2>/dev/null)
  BACKUP_DATE=$(echo "$MANIFEST" | python3 -c "import sys,json; print(json.load(sys.stdin).get('timestamp','?')[:16])" 2>/dev/null)
  MIGRATION_COUNT=$(echo "$MANIFEST" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('applied_migrations',[])))" 2>/dev/null)

  echo "  Date:        $BACKUP_DATE"
  echo "  Branch:      $BACKUP_BRANCH"
  echo "  Commit:      $BACKUP_COMMIT"
  echo "  Migrations:  $MIGRATION_COUNT applied"
else
  echo "  WARNING: No manifest found (old backup without code state info)"
  BACKUP_COMMIT=""
fi

# Production safety check
if [ "$TARGET" = "prod" ]; then
  echo ""
  echo "  *** WARNING: You are about to restore to PRODUCTION! ***"
  read -p "  Type 'RESTORE PROD' to confirm: " CONFIRM
  if [ "$CONFIRM" != "RESTORE PROD" ]; then
    echo "Cancelled."
    exit 0
  fi
else
  echo ""
  read -p "Proceed? [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
  fi
fi

# Save current branch to return to later
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

# Git checkout if we have a commit
if [ -n "$BACKUP_COMMIT" ]; then
  CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "")

  if [ "$CURRENT_COMMIT" != "$BACKUP_COMMIT" ]; then
    echo ""
    echo "==> Checking out backup's code state..."

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
      echo "ERROR: You have uncommitted changes. Commit or stash them first."
      exit 1
    fi

    git checkout "$BACKUP_COMMIT" --quiet
    echo "    Checked out $BACKUP_COMMIT"
  else
    echo ""
    echo "==> Already on the correct commit ($BACKUP_COMMIT)"
  fi
fi

# Deploy code to target
echo ""
echo "==> Deploying code to $TARGET..."

# Write BUILD_INFO before syncing
cat > "$SCRIPT_DIR/BUILD_INFO" <<BUILDEOF
GIT_COMMIT=$(git rev-parse HEAD)
GIT_BRANCH=${BACKUP_BRANCH:-$(git rev-parse --abbrev-ref HEAD)}
GIT_DIRTY=false
DEPLOY_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BUILDEOF

rsync -avz --delete \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='db.sqlite3' \
  --exclude='.env' \
  --exclude='.env2' \
  --exclude='staticfiles' \
  --exclude='media' \
  --exclude='*.egg-info' \
  --exclude='build' \
  --exclude='venv' \
  --exclude='todo.md' \
  ./ "$SERVER:$REMOTE_PATH/" --quiet

rm -f "$SCRIPT_DIR/BUILD_INFO"

echo "==> Rebuilding containers..."
ssh "$SERVER" "cd $REMOTE_PATH && docker compose build --quiet && docker compose up -d" 2>/dev/null

echo "==> Running migrations..."
ssh "$SERVER" "cd $REMOTE_PATH && docker compose exec -T app python manage.py migrate"

echo "==> Collecting static files..."
ssh "$SERVER" "cd $REMOTE_PATH && docker compose exec -T app python manage.py collectstatic --noinput" > /dev/null

# Restore database and media
echo ""
echo "==> Restoring backup on $TARGET..."
ssh "$SERVER" "cd $REMOTE_PATH && docker compose exec -T app python manage.py restore_backup $BACKUP_NAME --from-s3 --yes"

# Return to original branch
if [ -n "$ORIGINAL_BRANCH" ] && [ "$ORIGINAL_BRANCH" != "HEAD" ]; then
  echo ""
  echo "==> Returning to branch: $ORIGINAL_BRANCH"
  git checkout "$ORIGINAL_BRANCH" --quiet
fi

echo ""
echo "========================================"
echo "  Restore complete!"
echo "========================================"
echo ""
echo "  Backup $BACKUP_NAME restored to $TARGET ($HOST)"
if [ -n "$BACKUP_COMMIT" ]; then
  echo "  Code is at commit: $BACKUP_COMMIT"
fi
