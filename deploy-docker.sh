#!/bin/bash
set -e

# Deployment script for Docker-based deployment
# Usage: ./deploy-docker.sh [--prod] [--restart-caddy] [user@host]
#
# By default deploys to dev (DEV_HOST from .env)
# Use --prod to deploy to production (PRODUCTION_HOST from .env)
# Use --restart-caddy to restart Caddy after deploy (for config changes)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_PATH="/opt/basal"

# Parse arguments
DEPLOY_ENV="dev"
EXPLICIT_SERVER=""
RESTART_CADDY=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --prod)
      DEPLOY_ENV="prod"
      shift
      ;;
    --restart-caddy)
      RESTART_CADDY=true
      shift
      ;;
    *)
      EXPLICIT_SERVER="$1"
      shift
      ;;
  esac
done

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
  echo "⚠️  WARNING: You have uncommitted changes:"
  git status --short
  echo ""
  read -p "Deploy anyway? [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled. Commit your changes first."
    exit 0
  fi
fi

# Determine server based on environment or explicit argument
if [ -n "$EXPLICIT_SERVER" ]; then
  SERVER="$EXPLICIT_SERVER"
elif [ -f "$SCRIPT_DIR/.env" ]; then
  if [ "$DEPLOY_ENV" = "prod" ]; then
    HOST=$(grep -E '^PRODUCTION_HOST=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)
    ENV_VAR="PRODUCTION_HOST"
  else
    HOST=$(grep -E '^DEV_HOST=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)
    ENV_VAR="DEV_HOST"
  fi

  if [ -n "$HOST" ]; then
    SERVER="root@$HOST"
  else
    echo "Error: $ENV_VAR not set in .env"
    exit 1
  fi
else
  echo "Error: .env file not found and no server argument provided"
  exit 1
fi

echo "==> Deploying to $DEPLOY_ENV ($SERVER)..."

# Confirmation for production deployments
if [ "$DEPLOY_ENV" = "prod" ]; then
  read -p "⚠️  You are about to deploy to PRODUCTION. Continue? [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
  fi

  # Trigger backup before production deployment
  echo "==> Triggering database backup before deployment..."
  PRODUCTION_HOST=$(grep -E '^PRODUCTION_HOST=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)
  CRON_SECRET=$(grep -E '^CRON_SECRET=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)

  if [ -n "$PRODUCTION_HOST" ] && [ -n "$CRON_SECRET" ]; then
    backup_response=$(curl -s -w "\n%{http_code}" \
      -H "Authorization: Bearer $CRON_SECRET" \
      "https://$PRODUCTION_HOST/cron/backup/")

    http_code=$(echo "$backup_response" | tail -n1)
    body=$(echo "$backup_response" | sed '$d')

    if [ "$http_code" = "200" ]; then
      echo "✅ Backup completed successfully"
    else
      echo "❌ Backup failed (HTTP $http_code): $body"
      read -p "Continue deployment without backup? [y/N] " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
      fi
    fi
  else
    echo "⚠️  Warning: PRODUCTION_HOST or CRON_SECRET not found in .env, skipping backup"
    read -p "Continue deployment without backup? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Deployment cancelled."
      exit 0
    fi
  fi
fi

# Write build info for backup manifests
echo "==> Writing BUILD_INFO..."
cat > "$SCRIPT_DIR/BUILD_INFO" <<BUILDEOF
GIT_COMMIT=$(git rev-parse HEAD)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_DIRTY=$(git diff-index --quiet HEAD -- 2>/dev/null && echo "false" || echo "true")
DEPLOY_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BUILDEOF

# Sync code to server (excluding local dev files)
echo "==> Syncing code..."
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
  ./ "$SERVER:$REMOTE_PATH/"

rm -f "$SCRIPT_DIR/BUILD_INFO"

# Ensure dev deployment has email domain restrictions
if [ "$DEPLOY_ENV" = "dev" ]; then
  echo "==> Enforcing email domain allowlist for dev..."
  DEV_ALLOWED_DOMAINS="osogdata.dk,raakode.dk,sundkom.dk"
  ssh "$SERVER" "cd $REMOTE_PATH && grep -q '^EMAIL_ALLOWED_DOMAINS=' .env 2>/dev/null \
    && sed -i 's/^EMAIL_ALLOWED_DOMAINS=.*/EMAIL_ALLOWED_DOMAINS=$DEV_ALLOWED_DOMAINS/' .env \
    || echo 'EMAIL_ALLOWED_DOMAINS=$DEV_ALLOWED_DOMAINS' >> .env"
fi

# Build and restart containers
echo "==> Building and starting containers..."
ssh "$SERVER" "cd $REMOTE_PATH && docker compose build && docker compose up -d"

# Run migrations
echo "==> Running migrations..."
ssh "$SERVER" "cd $REMOTE_PATH && docker compose exec -T app python manage.py migrate"

# Collect static files
echo "==> Collecting static files..."
ssh "$SERVER" "cd $REMOTE_PATH && docker compose exec -T app python manage.py collectstatic --noinput"

# Restart Caddy if requested (for Caddyfile changes)
if [ "$RESTART_CADDY" = true ]; then
  echo "==> Restarting Caddy..."
  ssh "$SERVER" "cd $REMOTE_PATH && docker compose restart caddy"
fi

echo "==> Done!"
echo ""
echo "Useful commands:"
echo "  View logs:     ssh $SERVER 'cd $REMOTE_PATH && docker compose logs -f'"
echo "  App shell:     ssh $SERVER 'cd $REMOTE_PATH && docker compose exec app python manage.py shell'"
echo "  Restart:       ssh $SERVER 'cd $REMOTE_PATH && docker compose restart'"
echo "  Stop:          ssh $SERVER 'cd $REMOTE_PATH && docker compose down'"
