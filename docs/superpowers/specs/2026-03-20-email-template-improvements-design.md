# Email Template Improvements (OSO-207)

## Problem

The email template system needs several improvements:
- Users can create/delete/change template types — they should only edit content
- No coordinator email is sent when participants sign up for courses
- The course signup page doesn't show who the confirmation goes to
- Template variables are limited (missing registration deadline, instructors, etc.)
- The admin should show a "Kursusmateriale vedhæftes automatisk" note for the course reminder template

## Design

### 1. Template Model & Admin Lockdown

**New field on `EmailTemplate`:**
- `description` (TextField, blank=True) — read-only Danish text explaining when the template is sent and to whom

**New `EmailType`:**
- `COORDINATOR_SIGNUP` = "coordinator_signup", "Koordinator-tilmeldingsbekræftelse"
- Note: uses short value to stay within `max_length=30` on both `EmailTemplate.email_type` and `EmailLog.email_type`

**Migration** adds descriptions to the 3 existing templates and creates the new coordinator template:
- `SIGNUP_CONFIRMATION`: "Sendes til hver deltager ved kursustilmelding."
- `COURSE_REMINDER`: "Sendes til hver deltager 14 dage før kursusstart. Kursusmateriale vedhæftes automatisk."
- `SCHOOL_ENROLLMENT_CONFIRMATION`: "Sendes til koordinator når en skole tilmelder sig Basal."
- `COORDINATOR_SIGNUP`: "Sendes til skolens koordinator når deltagere tilmeldes et kursus. Indeholder oversigt over tilmeldte deltagere."

**Admin changes:**
- `email_type` and `description` are read-only
- `has_add_permission` returns False
- `has_delete_permission` returns False
- The `description` field is shown prominently (not collapsed)
- Use a dict mapping `EmailType` → variable list for the `available_variables` display (replacing the current if/else)

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

These new variables are available for admin customization; existing template content is not changed.

**New coordinator signup context** (`get_coordinator_signup_context`):
- `{{ coordinator_name }}` — coordinator Person name
- `{{ course_title }}` — `course.display_name`
- `{{ course_date }}` — formatted `course.start_date`
- `{{ course_end_date }}` — formatted `course.end_date`
- `{{ course_location }}` — `course.location.full_address`
- `{{ school_name }}` — school name
- `{{ participants_list }}` — HTML list of participant names from this signup batch (not all signups for the course)
- `{{ registration_deadline }}` — formatted `course.registration_deadline`
- `{{ instructors }}` — comma-separated instructor names

### 3. Coordinator Email Sending

**New function:** `send_coordinator_signup_confirmation(school, course, signups, override_email=None)`

Logic:
1. Look up coordinator: `school.people.filter(is_koordinator=True).first()`
2. Determine recipient:
   - If `override_email` provided → use that; `recipient_name` = "Override"
   - Else if coordinator exists and has email → use coordinator email/name
   - Else → log warning and skip (do not send)
3. Build context via `get_coordinator_signup_context()` (uses coordinator name if found, else "Koordinator")
4. Check `EMAIL_ALLOWED_DOMAINS` for the recipient (same as existing email functions)
5. Render template, add footer, send via Resend (same pattern as existing functions)
6. Log to `EmailLog` with `course` reference, `signup=None` (since this is per-batch, not per-signup)

**Called once per form submission** from `CourseSignupView.post()`, after all individual `send_signup_confirmation()` calls, alongside `send_course_signup_notification()` (admin notification unchanged).

### 4. Course Signup Page UI

The existing coordinator info display (lines 82-87 of `course_signup.html`) shows coordinator name/email/phone when a school is selected. The new coordinator confirmation section is placed **below the participant section**, separate from the existing info display.

At the bottom of the course signup form, after participant fields and before the submit button:

```
Bekræftelse sendes også til koordinator: {name} ({email})

[ ] Skal bekræftelsen sendes til en anden email?
    [email input - shown only when checkbox is checked]
```

- Coordinator name/email populated from existing AJAX data (`CheckSchoolSeatsView` already returns coordinator info)
- The section is hidden when no school is selected or when the school has no coordinator
- The override email input appears/hides via JavaScript on checkbox toggle
- Override email uses Django `EmailField` validation
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
- `EmailTemplate.email_type` and `EmailLog.email_type` max_length — unchanged (new value fits within 30)
