#!/bin/bash
set -e

# Deployment script for Docker-based deployment
# Usage: ./deploy-docker.sh [user@host]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_PATH="/opt/basal"

# Read PRODUCTION_HOST from .env if no argument provided
if [ -z "$1" ] && [ -f "$SCRIPT_DIR/.env" ]; then
    PRODUCTION_HOST=$(grep -E '^PRODUCTION_HOST=' "$SCRIPT_DIR/.env" | cut -d'=' -f2)
    if [ -n "$PRODUCTION_HOST" ]; then
        SERVER="root@$PRODUCTION_HOST"
    else
        echo "Error: PRODUCTION_HOST not set in .env and no server argument provided"
        exit 1
    fi
else
    SERVER="${1:-root@localhost}"
fi

echo "==> Deploying to $SERVER..."

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

# Build and restart containers
echo "==> Building and starting containers..."
ssh "$SERVER" "cd $REMOTE_PATH && docker compose build && docker compose up -d"

# Run migrations
echo "==> Running migrations..."
ssh "$SERVER" "cd $REMOTE_PATH && docker compose exec -T app python manage.py migrate"

# Collect static files
echo "==> Collecting static files..."
ssh "$SERVER" "cd $REMOTE_PATH && docker compose exec -T app python manage.py collectstatic --noinput"

echo "==> Done!"
echo ""
echo "Useful commands:"
echo "  View logs:     ssh $SERVER 'cd $REMOTE_PATH && docker compose logs -f'"
echo "  App shell:     ssh $SERVER 'cd $REMOTE_PATH && docker compose exec app python manage.py shell'"
echo "  Restart:       ssh $SERVER 'cd $REMOTE_PATH && docker compose restart'"
echo "  Stop:          ssh $SERVER 'cd $REMOTE_PATH && docker compose down'"
