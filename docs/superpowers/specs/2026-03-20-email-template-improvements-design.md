# Email Template Improvements (OSO-207)

## Problem

The email template system needs several improvements:
- Users can create/delete/change template types — they should only edit content
- No coordinator email is sent when participants sign up for courses
- The course signup page doesn't show who the confirmation goes to
- Template variables are limited (missing registration deadline, instructors, etc.)
- The "Kursusmateriale vedhæftes automatisk" admin note shows in wrong context

## Design

### 1. Template Model & Admin Lockdown

**New field on `EmailTemplate`:**
- `description` (TextField, blank=True) — read-only Danish text explaining when the template is sent and to whom

**New `EmailType`:**
- `COORDINATOR_SIGNUP_CONFIRMATION` = "coordinator_signup_confirmation", "Koordinator-tilmeldingsbekræftelse"

**Migration seeds all 4 templates** with descriptions:
- `SIGNUP_CONFIRMATION`: "Sendes til hver deltager ved kursustilmelding."
- `COURSE_REMINDER`: "Sendes til hver deltager 14 dage før kursusstart. Kursusmateriale vedhæftes automatisk."
- `SCHOOL_ENROLLMENT_CONFIRMATION`: "Sendes til koordinator når en skole tilmelder sig Basal."
- `COORDINATOR_SIGNUP_CONFIRMATION`: "Sendes til skolens koordinator når deltagere tilmeldes et kursus. Indeholder oversigt over tilmeldte deltagere."

**Admin changes:**
- `email_type` and `description` are read-only
- `has_add_permission` returns False
- `has_delete_permission` returns False
- The `description` field is shown prominently (not collapsed)

### 2. New Template Variables

**Course signup context** (`get_signup_context`) — add:
- `{{ registration_deadline }}` — formatted date from `course.registration_deadline`
- `{{ course_end_date }}` — formatted date from `course.end_date`
- `{{ instructors }}` — comma-separated names from `course.instructors.all()`
- `{{ spots_remaining }}` — integer from `course.spots_remaining`

**School enrollment context** (`get_school_enrollment_context`) — add:
- `{{ school_address }}` — from `school.adresse`
- `{{ school_municipality }}` — from `school.kommune`
- `{{ ean_nummer }}` — from `school.ean_nummer`

**New coordinator signup context** (`get_coordinator_signup_context`):
- `{{ coordinator_name }}` — coordinator Person name
- `{{ course_title }}` — `course.display_name`
- `{{ course_date }}` — formatted `course.start_date`
- `{{ course_end_date }}` — formatted `course.end_date`
- `{{ course_location }}` — `course.location.full_address`
- `{{ school_name }}` — school name
- `{{ participants_list }}` — HTML list of participant names signed up
- `{{ registration_deadline }}` — formatted `course.registration_deadline`
- `{{ instructors }}` — comma-separated instructor names

**Update admin `available_variables`** display to show correct variables per email type (4 groups now).

### 3. Coordinator Email Sending

**New function:** `send_coordinator_signup_confirmation(school, course, signups, override_email=None)`

Logic:
1. Look up coordinator: `school.people.filter(is_koordinator=True).first()`
2. If `override_email` provided, use that instead of coordinator's email
3. Build context via `get_coordinator_signup_context()`
4. Render template, add footer, send via Resend (same pattern as existing functions)
5. Log to `EmailLog` with course reference

**Called from** `CourseSignupView.post()` after existing `send_signup_confirmation()` calls, alongside `send_course_signup_notification()` (admin notification unchanged).

### 4. Course Signup Page UI

At the bottom of the course signup form, after participant fields and before the submit button:

```
Bekræftelse sendes også til koordinator: {name} ({email})

[ ] Skal bekræftelsen sendes til en anden email?
    [email input - shown only when checkbox is checked]
```

- Coordinator name/email populated from existing AJAX data (`CheckSchoolSeatsView` already returns coordinator info)
- The override email input appears/hides via JavaScript on checkbox toggle
- Override email submitted as form field `coordinator_email_override`
- View passes `override_email` to `send_coordinator_signup_confirmation()`

### 5. Files Changed

- `apps/emails/models.py` — add `description` field, new EmailType
- `apps/emails/admin.py` — read-only type/description, disable add/delete, update variable display
- `apps/emails/services.py` — new context builders, new send function, extend existing contexts
- `apps/emails/migrations/XXXX_*.py` — add description field, seed coordinator template
- `apps/signups/views.py` — call coordinator email, pass override
- `apps/signups/templates/signups/course_signup.html` — coordinator confirmation UI
- `apps/signups/forms.py` — optional override email field

### 6. What Does NOT Change

- `send_course_signup_notification()` (admin notification) — unchanged
- `send_school_enrollment_confirmation()` — unchanged (just gets more context variables)
- Existing template content in DB — unchanged (users edit via admin)
- Course reminder attachment logic — unchanged
- Bulk email system — unchanged
