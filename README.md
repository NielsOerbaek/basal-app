# Basal

A course enrollment management system for teacher training programs. Built with Django 5 and designed for managing schools, courses, and participant registrations.

## Overview

Basal handles:
- **School Enrollment**: Track schools enrolled in the teacher training program
- **Course Management**: Create and publish training courses
- **Seat Allocation**: Manage course seats with business rules (3 base seats per school, 1 additional "forankringsplads" after 1 year, purchasable extra seats)
- **Course Sign-ups**: Track participant registrations
- **Contact History**: Log all interactions with schools
- **Activity Auditing**: Track all data changes
- **Email Automation**: Send course confirmations and reminders

## Main Data Models

### Schools (`apps/schools`)
- `School` - Schools enrolled in the program (name, address, kommune, enrollment date, active status)
- `SeatPurchase` - Additional seats purchased by schools
- `Person` - Contact persons at schools (roles: Koordinator, Skoleleder, Udskolingsleder)
- `SchoolComment` - Comments about schools
- `Invoice` - Invoices for schools (status: planned, sent, paid)

### Courses (`apps/courses`)
- `Course` - Training courses (title, dates, location, capacity, teachers, materials, published status)
- `CourseSignUp` - Participant registrations linked to school and course

### Contacts (`apps/contacts`)
- `ContactTime` - Contact history/log entries with schools

### Emails (`apps/emails`)
- `EmailTemplate` - Editable email templates with Django template variables
- `EmailLog` - Log of all sent emails

### Audit (`apps/audit`)
- `ActivityLog` - Audit trail tracking CREATE/UPDATE/DELETE actions across all models

## Tech Stack

- **Framework**: Django 5.x
- **Database**: PostgreSQL 16
- **Frontend**: Bootstrap 5, HTMX, django-crispy-forms
- **Email**: Resend
- **Rich Text**: django-summernote
- **Static Files**: WhiteNoise
- **WSGI Server**: Gunicorn
- **Reverse Proxy**: Caddy (automatic HTTPS)
- **Backups**: Backblaze B2 (via boto3 S3-compatible API)

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 16+

### Local Development

1. Clone the repository and install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. Copy the environment file and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Create demo data (optional):
   ```bash
   python manage.py create_demo_data
   ```

5. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Deployment

The application is deployed using Docker Compose with three services:

| Service | Container | Description |
|---------|-----------|-------------|
| `db` | PostgreSQL 16 | Database with persistent volume |
| `app` | Django/Gunicorn | Application server (3 workers) |
| `caddy` | Caddy 2 | Reverse proxy with automatic HTTPS |

Deploy with:
```bash
./deploy-docker.sh
```

See `DEPLOYMENT.md` for detailed deployment instructions.

## Management Commands

### `create_demo_data`
Creates comprehensive demo/test data including schools, courses, and signups.
```bash
python manage.py create_demo_data
python manage.py create_demo_data --clear  # Clear existing data first
```

### `backup_database`
Backs up the PostgreSQL database to Backblaze B2 with automatic cleanup.
```bash
python manage.py backup_database
python manage.py backup_database --retention-days 60
python manage.py backup_database --local-only  # Skip B2 upload
```
Requires: `B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_ENDPOINT`

### `import_schools`
Imports schools from Excel files.
```bash
python manage.py import_schools path/to/file.xlsx
python manage.py import_schools path/to/file.xlsx --dry-run
python manage.py import_schools path/to/file.xlsx --sheet 1 --start-row 5
```

### `send_course_reminders`
Sends reminder emails 2 days before courses start.
```bash
python manage.py send_course_reminders
python manage.py send_course_reminders --dry-run
python manage.py send_course_reminders --days-before 3
```

### `test_email`
Tests email templates and delivery.
```bash
python manage.py test_email signup_confirmation
python manage.py test_email course_reminder --to test@example.com
python manage.py test_email course_reminder --attachment materials.pdf
```

## Automated Tasks

GitHub Actions workflows handle scheduled tasks:

| Workflow | Schedule | Description |
|----------|----------|-------------|
| `send-reminders.yml` | Daily 08:00 UTC | Sends course reminders |
| `backup-database.yml` | Daily 01:00 UTC | Database backups to B2 |

Both use authenticated endpoints with `CRON_SECRET` bearer token.

## Business Logic

- Schools receive **3 base seats** upon enrollment
- After **1 year**: schools receive 1 additional "forankringsplads" seat
- Additional seats can be **purchased**
- All signups count against available seats
- Public signup forms only show **published courses**

## Configuration

Key environment variables:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |
| `RESEND_API_KEY` | Resend email API key |
| `DEFAULT_FROM_EMAIL` | Default sender email address |
| `CRON_SECRET` | Secret for authenticated cron endpoints |
| `B2_*` | Backblaze B2 credentials for backups |

## License

Proprietary software.
