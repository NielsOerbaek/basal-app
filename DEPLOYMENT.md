# Deployment Guide

This application can be deployed using Docker Compose on any server with Docker installed.

## Prerequisites

- A server with Docker and Docker Compose installed
- A domain pointing to the server
- SSH access to the server

## Quick Start

1. **Install Docker on your server:**
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```

2. **Clone or copy the application to your server:**
   ```bash
   # On your local machine
   ./deploy-docker.sh user@your-server
   ```

3. **Configure environment variables on the server:**
   ```bash
   ssh user@your-server
   cd /opt/basal
   cp .env.production.example .env
   nano .env  # Edit with your values
   ```

4. **Start the application:**
   ```bash
   docker compose up -d
   ```

5. **Run migrations and create superuser:**
   ```bash
   docker compose exec app python manage.py migrate
   docker compose exec app python manage.py createsuperuser
   ```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DOMAIN` | Your domain (e.g., `basal.example.com`) | Yes |
| `SECRET_KEY` | Django secret key | Yes |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `POSTGRES_DB` | Database name (default: `basal`) | No |
| `POSTGRES_USER` | Database user (default: `basal`) | No |
| `RESEND_API_KEY` | Resend API key for emails | No |
| `DEFAULT_FROM_EMAIL` | Sender email address | No |
| `CRON_SECRET` | Secret for cron endpoint authentication | No |

## Services

The application consists of three services:

- **db**: PostgreSQL 16 database
- **app**: Django application (Gunicorn)
- **caddy**: Reverse proxy with automatic HTTPS

## Common Operations

```bash
# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f app

# Restart all services
docker compose restart

# Restart specific service
docker compose restart app

# Run Django management command
docker compose exec app python manage.py <command>

# Access Django shell
docker compose exec app python manage.py shell

# Create database backup
docker compose exec db pg_dump -U basal basal > backup.sql

# Restore database backup
docker compose exec -T db psql -U basal basal < backup.sql

# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v
```

## Updating the Application

```bash
# From your local machine
./deploy-docker.sh user@your-server
```

Or manually on the server:
```bash
cd /opt/basal
git pull  # or rsync new code
docker compose build
docker compose up -d
docker compose exec app python manage.py migrate
docker compose exec app python manage.py collectstatic --noinput
```

## SSL Certificates

Caddy automatically obtains and renews SSL certificates from Let's Encrypt. No manual configuration needed - just ensure your domain points to the server before starting.

## Moving to a New Server

1. Create a database backup on the old server
2. Install Docker on the new server
3. Copy the application code and `.env` file
4. Update DNS to point to the new server
5. Start the application
6. Restore the database backup
