#!/bin/bash
set -e

cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Basal development environment...${NC}"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${RED}No virtual environment found. Create one with: python -m venv .venv${NC}"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your settings, then run this script again.${NC}"
    exit 1
fi

# Extract DATABASE_URL from .env file
DATABASE_URL=$(grep -E '^DATABASE_URL=' .env | cut -d'=' -f2-)

# Extract postgres credentials from DATABASE_URL
# Format: postgresql://user:password@host:port/database
if [ -n "$DATABASE_URL" ]; then
    export POSTGRES_USER=$(echo "$DATABASE_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
    export POSTGRES_PASSWORD=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
    export POSTGRES_DB=$(echo "$DATABASE_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')
fi

# Start PostgreSQL container if not running
if ! docker ps --format '{{.Names}}' | grep -q 'basal-postgres'; then
    echo -e "${YELLOW}Starting PostgreSQL container...${NC}"
    docker compose up -d db

    # Wait for PostgreSQL to be ready
    echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
    until docker compose exec -T db pg_isready -U basal -d basal > /dev/null 2>&1; do
        sleep 1
    done
    echo -e "${GREEN}PostgreSQL is ready.${NC}"
else
    echo -e "${GREEN}PostgreSQL container already running.${NC}"
fi

# Run migrations
echo -e "${YELLOW}Running migrations...${NC}"
python manage.py migrate

# Start development server
echo -e "${GREEN}Starting development server at http://localhost:8000${NC}"
python manage.py runserver
