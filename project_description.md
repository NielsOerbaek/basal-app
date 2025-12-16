# MVP Specification: Course Enrollment Management System

## 1. Executive Summary

This document specifies a Minimum Viable Product (MVP) for a web application that manages school enrollments in a teacher training program. The system tracks schools, courses, sign-ups, employee interactions, and contact history.

### Core Value Proposition
- Centralized management of school enrollments and course sign-ups
- Public-facing forms for schools to self-register for courses
- Contact history tracking for relationship management
- Data export capabilities for reporting

---

## 2. Technical Architecture

### 2.1 Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Backend** | Django 5.x | Mature, batteries-included, excellent admin capabilities, strong ORM |
| **Database** | PostgreSQL 16 | Robust, excellent Django support, handles complex queries well |
| **Frontend** | Django Templates + HTMX | Minimal JS complexity, maintains monolith simplicity, great for CRUD apps |
| **Component Library** | django-crispy-forms + Bootstrap 5 | Well-maintained, accessible, familiar to most developers |
| **Export** | openpyxl | Standard library for Excel generation |
| **Authentication** | Django built-in auth | Simple, secure, sufficient for MVP |
| **Deployment** | Docker + Docker Compose | Reproducible environments, easy deployment |

### 2.2 Project Structure

```
course_enrollment/
├── manage.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
│
├── config/                    # Project configuration
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── core/                  # Shared utilities, base templates
│   │   ├── templates/
│   │   │   └── core/
│   │   │       ├── base.html
│   │   │       └── components/
│   │   ├── views.py           # Dashboard view
│   │   └── export.py          # Excel export utilities
│   │
│   ├── schools/               # School management
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   └── templates/schools/
│   │
│   ├── courses/               # Course & sign-up management
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   └── templates/courses/
│   │
│   ├── contacts/              # Contact history tracking
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   └── templates/contacts/
│   │
│   └── accounts/              # User management
│       ├── models.py
│       ├── views.py
│       ├── forms.py
│       ├── urls.py
│       └── templates/accounts/
│
├── static/
│   ├── css/
│   └── js/
│
└── templates/                 # Global templates
    └── registration/          # Auth templates
```

---

## 3. Data Models

### 3.1 Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│   School    │       │  CourseSignUp   │       │   Course    │
├─────────────┤       ├─────────────────┤       ├─────────────┤
│ id (PK)     │──┐    │ id (PK)         │    ┌──│ id (PK)     │
│ name        │  │    │ school_id (FK)  │────┤  │ title       │
│ location    │  └────│ course_id (FK)  │────┘  │ datetime    │
│ contact_..  │       │ participant_... │       │ location    │
│ comments    │       │ participant_... │       │ comment     │
│ created_at  │       │ attended        │       │ created_at  │
│ updated_at  │       │ created_at      │       │ updated_at  │
└─────────────┘       └─────────────────┘       └─────────────┘
       │
       │         ┌─────────────────┐       ┌─────────────┐
       │         │   ContactTime   │       │  Employee   │
       │         ├─────────────────┤       ├─────────────┤
       └─────────│ school_id (FK)  │       │ id (PK)     │
                 │ employee_id(FK) │───────│ user (1:1)  │
                 │ contacted_at    │       │ created_at  │
                 │ comment         │       └─────────────┘
                 │ created_at      │
                 └─────────────────┘
```

### 3.2 Model Definitions

```python
# apps/schools/models.py
from django.db import models

class School(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
```

```python
# apps/courses/models.py
from django.db import models

class Course(models.Model):
    title = models.CharField(max_length=255)
    datetime = models.DateTimeField()
    location = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField(default=30)
    comment = models.TextField(blank=True)
    is_published = models.BooleanField(
        default=False,
        help_text="Published courses appear on public sign-up forms"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-datetime']

    def __str__(self):
        return f"{self.title} - {self.datetime.strftime('%Y-%m-%d')}"

    @property
    def signup_count(self):
        return self.signups.count()

    @property
    def attendance_count(self):
        return self.signups.filter(attended=True).count()


class CourseSignUp(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='course_signups'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='signups'
    )
    participant_name = models.CharField(max_length=255)
    participant_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Job title or role"
    )
    attended = models.BooleanField(null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['school__name', 'participant_name']

    def __str__(self):
        return f"{self.participant_name} ({self.school.name})"
```

```python
# apps/contacts/models.py
from django.db import models

class ContactTime(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='contact_history'
    )
    employee = models.ForeignKey(
        'accounts.Employee',
        on_delete=models.SET_NULL,
        null=True,
        related_name='contacts_made'
    )
    contacted_at = models.DateTimeField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-contacted_at']

    def __str__(self):
        return f"{self.school.name} - {self.contacted_at.strftime('%Y-%m-%d')}"
```

```python
# apps/accounts/models.py
from django.db import models
from django.contrib.auth.models import User

class Employee(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
```

---

## 4. Feature Specifications

### 4.1 Authentication & Authorization

**User Roles (MVP):**
- **Staff**: Full access to all features (Django `is_staff` flag)
- **Superuser**: Staff access plus user management

**Implementation:**
- Use Django's built-in `@login_required` decorator
- Use `@staff_member_required` for admin views
- Public sign-up forms require no authentication

### 4.2 CRUD Operations Pattern

All entity management follows a consistent pattern:

**List View:**
- Paginated table (25 items per page)
- Search/filter capabilities
- Export to Excel button
- "Add New" button

**Detail View (Read-Only Default):**
- Display all fields in a clean layout
- "Edit" button to switch to edit mode
- "Delete" button with confirmation modal
- Related items displayed (e.g., school's contact history)

**Edit Mode:**
- Form fields become editable
- "Save" and "Cancel" buttons
- Validation feedback

**Implementation with HTMX:**
```html
<!-- Example: Detail view with edit toggle -->
<div id="school-detail">
    {% if edit_mode %}
        <form hx-post="{% url 'schools:update' school.pk %}"
              hx-target="#school-detail"
              hx-swap="outerHTML">
            {% crispy form %}
            <button type="submit" class="btn btn-primary">Save</button>
            <button type="button" 
                    hx-get="{% url 'schools:detail' school.pk %}"
                    hx-target="#school-detail"
                    class="btn btn-secondary">Cancel</button>
        </form>
    {% else %}
        <dl class="row">
            <dt class="col-sm-3">Name</dt>
            <dd class="col-sm-9">{{ school.name }}</dd>
            <!-- ... other fields ... -->
        </dl>
        <button hx-get="{% url 'schools:edit' school.pk %}"
                hx-target="#school-detail"
                class="btn btn-outline-primary">Edit</button>
        <button hx-get="{% url 'schools:delete-confirm' school.pk %}"
                hx-target="#modal-container"
                class="btn btn-outline-danger">Delete</button>
    {% endif %}
</div>
```

### 4.3 Public Course Sign-Up Form

**URL:** `/signup/` (no authentication required)

**Flow:**
1. School selects from published courses
2. Enters school name (autocomplete from existing, or add new)
3. Enters participant details
4. Submits sign-up
5. Confirmation page displayed

**Form Fields:**
- Course selection (dropdown of published future courses)
- School name (autocomplete + "Register new school" option)
- If new school: location, contact name, contact email, contact phone
- Participant name (required)
- Participant title (optional)

**Validation:**
- Course must be published and in the future
- All required fields must be filled
- Email format validation

### 4.4 Roll Call View

**URL:** `/courses/<id>/rollcall/`

**Features:**
- List of all sign-ups for the course
- Grouped by school
- Quick toggle buttons: "Present" / "Absent"
- Real-time save with HTMX (no page reload)
- Summary stats at top (total, present, absent, unmarked)

```html
<!-- Roll call item -->
<tr>
    <td>{{ signup.participant_name }}</td>
    <td>{{ signup.school.name }}</td>
    <td>
        <div class="btn-group" role="group">
            <button hx-post="{% url 'courses:mark-attendance' signup.pk %}"
                    hx-vals='{"attended": "true"}'
                    hx-swap="outerHTML"
                    hx-target="closest tr"
                    class="btn btn-sm {% if signup.attended == True %}btn-success{% else %}btn-outline-success{% endif %}">
                Present
            </button>
            <button hx-post="{% url 'courses:mark-attendance' signup.pk %}"
                    hx-vals='{"attended": "false"}'
                    hx-swap="outerHTML"
                    hx-target="closest tr"
                    class="btn btn-sm {% if signup.attended == False %}btn-danger{% else %}btn-outline-danger{% endif %}">
                Absent
            </button>
        </div>
    </td>
</tr>
```

### 4.5 Dashboard / Home Page

**URL:** `/` (requires authentication)

**Stats Cards:**
- Total enrolled schools
- Pending sign-ups (for future courses)
- Courses this month
- Total participants trained (attended = True)

**Upcoming Courses Table:**
- Next 5 courses
- Date, title, location
- Sign-up count / capacity
- Progress bar showing fill rate

**Recent Activity:**
- Last 10 contact entries
- Last 10 sign-ups

### 4.6 Excel Export

**Implementation:**
```python
# apps/core/export.py
import openpyxl
from django.http import HttpResponse

def export_queryset_to_excel(queryset, fields, filename):
    """
    Generic Excel export utility.
    
    Args:
        queryset: Django queryset to export
        fields: List of (field_name, header_label) tuples
        filename: Output filename (without extension)
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Headers
    for col, (_, header) in enumerate(fields, start=1):
        ws.cell(row=1, column=col, value=header)
    
    # Data
    for row_num, obj in enumerate(queryset, start=2):
        for col, (field, _) in enumerate(fields, start=1):
            value = getattr(obj, field, '')
            if callable(value):
                value = value()
            ws.cell(row=row_num, column=col, value=str(value))
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    wb.save(response)
    return response
```

**Export Available For:**
- Schools list
- Courses list
- Sign-ups (filterable by course)
- Contact history (filterable by school)

### 4.7 User Management

**Available to Superusers Only**

**Features:**
- List all users
- Create new user (with Employee profile auto-created)
- Edit user (name, email, active status, staff status)
- Reset password (sends email or displays temporary password)
- Deactivate user (soft delete - sets `is_active=False`)

---

## 5. URL Structure

```python
# config/urls.py
urlpatterns = [
    path('', include('apps.core.urls')),
    path('schools/', include('apps.schools.urls')),
    path('courses/', include('apps.courses.urls')),
    path('contacts/', include('apps.contacts.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('signup/', include('apps.courses.public_urls')),  # Public forms
]

# apps/schools/urls.py
app_name = 'schools'
urlpatterns = [
    path('', views.SchoolListView.as_view(), name='list'),
    path('create/', views.SchoolCreateView.as_view(), name='create'),
    path('<int:pk>/', views.SchoolDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.SchoolEditView.as_view(), name='edit'),
    path('<int:pk>/update/', views.SchoolUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.SchoolDeleteView.as_view(), name='delete'),
    path('export/', views.SchoolExportView.as_view(), name='export'),
]

# apps/courses/urls.py
app_name = 'courses'
urlpatterns = [
    path('', views.CourseListView.as_view(), name='list'),
    path('create/', views.CourseCreateView.as_view(), name='create'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.CourseEditView.as_view(), name='edit'),
    path('<int:pk>/rollcall/', views.RollCallView.as_view(), name='rollcall'),
    path('signups/', views.SignUpListView.as_view(), name='signup-list'),
    path('signups/<int:pk>/attendance/', views.MarkAttendanceView.as_view(), name='mark-attendance'),
    path('export/', views.CourseExportView.as_view(), name='export'),
    path('signups/export/', views.SignUpExportView.as_view(), name='signup-export'),
]

# apps/courses/public_urls.py (no auth required)
urlpatterns = [
    path('', views.PublicSignUpView.as_view(), name='public-signup'),
    path('success/', views.SignUpSuccessView.as_view(), name='signup-success'),
]
```

---

## 6. UI/UX Guidelines

### 6.1 Layout

```
┌────────────────────────────────────────────────────────────┐
│  Logo    Schools  Courses  Contacts       [User] [Logout]  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─ Page Title ─────────────────────── [Action Button] ─┐  │
│  │                                                      │  │
│  │  Content Area                                        │  │
│  │                                                      │  │
│  │  - Tables with pagination                            │  │
│  │  - Forms                                             │  │
│  │  - Detail views                                      │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 6.2 Component Patterns

**Tables:**
- Striped rows for readability
- Sortable column headers (where applicable)
- Action buttons in rightmost column
- Responsive (horizontal scroll on mobile)

**Forms:**
- Labels above inputs
- Clear validation error messages
- Required field indicators
- Logical field grouping

**Buttons:**
- Primary action: filled blue
- Secondary action: outlined
- Destructive action: red (with confirmation)

### 6.3 Accessibility

- Proper heading hierarchy
- Form labels associated with inputs
- Sufficient color contrast
- Keyboard navigation support
- Focus indicators

---

## 7. Development Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Project setup (Django, PostgreSQL, Docker)
- [ ] Base templates and styling
- [ ] Authentication system
- [ ] Employee model and user management

### Phase 2: Core Entities (Week 2)
- [ ] School CRUD
- [ ] Course CRUD
- [ ] Sign-up CRUD
- [ ] Contact history CRUD

### Phase 3: Special Features (Week 3)
- [ ] Public sign-up form
- [ ] Roll call view
- [ ] Dashboard with stats
- [ ] Excel export

### Phase 4: Polish (Week 4)
- [ ] UI refinements
- [ ] Testing
- [ ] Documentation
- [ ] Deployment configuration

---

## 8. Configuration & Environment

### 8.1 Environment Variables

```bash
# .env.example
DEBUG=False
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgres://user:password@localhost:5432/course_enrollment
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Email (for password reset)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=password
EMAIL_USE_TLS=True
```

### 8.2 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgres://postgres:postgres@db:5432/course_enrollment
    volumes:
      - static_volume:/app/staticfiles

  db:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=course_enrollment
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres

volumes:
  postgres_data:
  static_volume:
```

---

## 9. Testing Strategy

### Unit Tests
- Model validation
- Form validation
- Export utilities

### Integration Tests
- CRUD operations
- Authentication flows
- Public sign-up flow

### Manual Testing Checklist
- [ ] Can create/edit/delete each entity type
- [ ] Public sign-up form works without login
- [ ] Roll call updates persist correctly
- [ ] Excel exports contain correct data
- [ ] Dashboard stats are accurate
- [ ] User management works (superuser only)

---

## 10. Future Considerations (Post-MVP)

These items are explicitly **out of scope** for MVP but noted for future planning:

1. **Email notifications** - Confirmation emails for sign-ups
2. **Material tracking** - Track which schools have received materials
3. **Payment integration** - Handle fees for additional spots/materials
4. **Reporting dashboard** - More detailed analytics
5. **API** - REST API for potential integrations
6. **Audit logging** - Track who changed what and when
7. **Multi-tenancy** - Support for multiple programs/organizations

---

## 11. Appendix: Dependencies

```toml
# pyproject.toml (relevant dependencies)
[project]
dependencies = [
    "django>=5.0,<6.0",
    "psycopg[binary]>=3.1",
    "django-crispy-forms>=2.1",
    "crispy-bootstrap5>=2024.2",
    "django-htmx>=1.17",
    "openpyxl>=3.1",
    "python-dotenv>=1.0",
    "whitenoise>=6.6",  # Static file serving
    "gunicorn>=21.0",   # Production server
]

[project.optional-dependencies]
dev = [
    "pytest-django>=4.5",
    "factory-boy>=3.3",
    "django-debug-toolbar>=4.2",
]
```

---

This specification should provide a solid foundation for building the MVP. Want me to elaborate on any particular section, or shall we start implementing specific components?
