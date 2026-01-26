# Course Signup Authentication & Instant School Enrollment

## Overview

Add basic authentication to the course signup form and streamline school enrollment to be instant (no admin processing required).

## Goals

1. Schools can sign up for courses immediately after enrolling in Basal
2. Course signup form is protected by school-specific passwords
3. Staff can bypass authentication and sign up anyone
4. Relevant users get notified when new schools enroll

## Design

### 1. School Model Changes

Add two fields to `School` for authentication:

```python
# apps/schools/models.py
signup_password = models.CharField(max_length=20, blank=True, verbose_name="Tilmeldingskode")
signup_token = models.CharField(max_length=32, blank=True, db_index=True, verbose_name="Tilmeldingstoken")
```

- `signup_password`: Pronounceable password (consonant-vowel pairs, e.g., "bafimoku")
- `signup_token`: Random 32-character string for URL-based authentication

Helper functions:
- `generate_pronounceable_password()` - creates passwords like "bafimoku", "tokaluri"
- `generate_token()` - creates random 32-char alphanumeric string

### 2. School Signup Flow (Instant Enrollment)

Current flow: Form → SchoolSignup record → Admin processes → School enrolled

New flow: Form → School enrolled immediately → Email with credentials

**On form submission:**
1. If existing school selected:
   - Set `enrolled_at = today` (if not already set)
   - Generate `signup_password` and `signup_token`
2. If new school:
   - Create School with name, address, municipality, `enrolled_at = today`
   - Generate credentials
3. Send confirmation email containing:
   - Welcome message
   - The pronounceable password
   - Direct link: `{SITE_URL}/tilmelding/kursus/?token={token}`
4. Send notification email to subscribed staff users
5. Redirect to success page

**Remove:** `SchoolSignup` model and related admin processing workflow.

### 3. Course Signup Authentication

Three authentication modes:

**Mode A - Token in URL:**
- URL: `/tilmelding/kursus/?token=abc123`
- Lookup school by `signup_token`
- If valid: show form with school pre-selected and locked
- If invalid: show error message

**Mode B - Password entry:**
- URL: `/tilmelding/kursus/`
- Show password input field, form hidden below
- User enters password → AJAX POST to validate
- If valid: store school ID in session, reveal form with school locked
- If invalid: show error message

**Mode C - Staff bypass:**
- User is logged in with `is_staff=True`
- Form visible immediately
- School dropdown shows all enrolled schools (editable, not locked)

**Session handling:**
- Store authenticated school ID in session key `course_signup_school_id`
- Session persists so users don't re-enter password on page refresh
- Clear session on successful signup or explicit logout

### 4. User Notification Preferences

New model for user settings:

```python
# apps/accounts/models.py
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    notify_on_school_signup = models.BooleanField(
        default=False,
        verbose_name="Modtag email ved ny skoletilmelding"
    )
```

- Auto-created via signal when User is created
- Checkbox added to `UserUpdateForm`
- Staff with permission to edit users can toggle this for others

**Notification email contains:**
- School name
- Municipality
- Contact person name and email
- Link to school detail page

### 5. School Detail Page - Credentials Display

Add a "Tilmeldingsoplysninger" section (only for enrolled schools):

- **Password:** Hidden by default, reveal button, copy button
- **Direct link:** Full URL with token, copy button
- **Regenerate button:** Creates new password + token (with confirmation)

Layout:
```
┌─────────────────────────────────────────────────┐
│ Tilmeldingsoplysninger                          │
├─────────────────────────────────────────────────┤
│ Kode:  ●●●●●●●●  [👁 Vis] [📋 Kopiér]           │
│ Link:  https://...?token=... [📋 Kopiér]        │
│                                                 │
│ [Generer ny kode]                               │
└─────────────────────────────────────────────────┘
```

## Files to Modify

### Models
- `apps/schools/models.py` - Add `signup_password`, `signup_token` fields
- `apps/accounts/models.py` - Add `UserProfile` model

### Views
- `apps/signups/views.py` - Rewrite `SchoolSignupView`, add auth to `CourseSignupView`
- `apps/schools/views.py` - Add regenerate credentials endpoint

### Forms
- `apps/signups/forms.py` - Simplify `SchoolSignupForm`
- `apps/accounts/forms.py` - Add `notify_on_school_signup` checkbox

### Templates
- `apps/signups/templates/signups/course_signup.html` - Add password field, JS for reveal
- `apps/schools/templates/schools/school_detail.html` - Add credentials section

### Emails
- `apps/emails/services.py` - Add `send_school_enrollment_confirmation()`, `send_school_signup_notification()`

### Migrations
- `apps/schools/migrations/` - Add password/token fields
- `apps/accounts/migrations/` - Add UserProfile model

### Removals
- `apps/signups/models.py` - Remove `SchoolSignup` model
- `apps/signups/admin.py` - Remove SchoolSignup admin
- Related migrations for SchoolSignup removal

## Password Generation

Pronounceable passwords use alternating consonants and vowels:

```python
import secrets

CONSONANTS = 'bdfgklmnprstvz'
VOWELS = 'aeiou'

def generate_pronounceable_password(syllables=4):
    """Generate password like 'bafimoku' (4 syllables = 8 chars)."""
    password = ''
    for _ in range(syllables):
        password += secrets.choice(CONSONANTS)
        password += secrets.choice(VOWELS)
    return password
```

## Security Considerations

- Passwords stored in plaintext (intentional - employees need to read them)
- Tokens are URL-safe and indexed for fast lookup
- Session-based auth clears on browser close
- Staff bypass requires Django authentication
- Regenerate function allows credential rotation if compromised
