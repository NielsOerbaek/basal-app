import logging

import resend
from django.conf import settings
from django.template import Context, Template
from django.utils.formats import date_format

from .models import EmailLog, EmailTemplate, EmailType

logger = logging.getLogger(__name__)


def render_template(template_string, context_dict):
    """Render a template string with the given context."""
    template = Template(template_string)
    context = Context(context_dict)
    return template.render(context)


def get_signup_context(signup):
    """Build template context from a CourseSignUp instance."""
    return {
        "participant_name": signup.participant_name,
        "participant_email": signup.participant_email,
        "participant_title": signup.participant_title,
        "school_name": signup.school.name,
        "course_title": signup.course.title,
        "course_date": date_format(signup.course.start_date, "j. F Y"),
        "course_location": signup.course.location,
    }


def send_email(email_type, signup, attachments=None):
    """
    Send an email using a template.

    Args:
        email_type: EmailType value
        signup: CourseSignUp instance
        attachments: Optional list of dicts with 'filename', 'content' (bytes)

    Returns:
        True if successful, False otherwise
    """
    try:
        template = EmailTemplate.objects.get(email_type=email_type, is_active=True)
    except EmailTemplate.DoesNotExist:
        logger.warning(f"No active template found for email type: {email_type}")
        return False

    context = get_signup_context(signup)
    subject = render_template(template.subject, context)
    body_html = render_template(template.body_html, context)

    # Check if we have a Resend API key
    if not settings.RESEND_API_KEY:
        # Log to console in development
        logger.info(f"[EMAIL] To: {signup.participant_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body: {body_html[:200]}...")
        EmailLog.objects.create(
            email_type=email_type,
            recipient_email=signup.participant_email,
            recipient_name=signup.participant_name,
            subject=subject,
            course=signup.course,
            signup=signup,
            success=True,
            error_message="[DEV MODE - not actually sent]",
        )
        return True

    try:
        resend.api_key = settings.RESEND_API_KEY

        email_params = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [signup.participant_email],
            "subject": subject,
            "html": body_html,
        }

        if attachments:
            email_params["attachments"] = attachments

        resend.Emails.send(email_params)

        EmailLog.objects.create(
            email_type=email_type,
            recipient_email=signup.participant_email,
            recipient_name=signup.participant_name,
            subject=subject,
            course=signup.course,
            signup=signup,
            success=True,
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        EmailLog.objects.create(
            email_type=email_type,
            recipient_email=signup.participant_email,
            recipient_name=signup.participant_name,
            subject=subject,
            course=signup.course,
            signup=signup,
            success=False,
            error_message=str(e),
        )
        return False


def send_signup_confirmation(signup):
    """Send signup confirmation email."""
    return send_email(EmailType.SIGNUP_CONFIRMATION, signup)


def send_course_reminder(signup, attachments=None):
    """Send course reminder email with optional attachments (e.g., course materials)."""
    return send_email(EmailType.COURSE_REMINDER, signup, attachments=attachments)


def send_school_enrollment_confirmation(school, contact_email, contact_name):
    """
    Send enrollment confirmation email to school contact.

    Args:
        school: School instance with credentials
        contact_email: Email address of contact person
        contact_name: Name of contact person

    Returns:
        True if successful, False otherwise
    """
    subject = f"Velkommen til Basal - {school.name}"

    signup_url = f"{settings.SITE_URL}/signup/course/?token={school.signup_token}"

    body_html = f"""
    <p>Hej {contact_name},</p>

    <p>Tak for jeres tilmelding til Basal! {school.name} er nu tilmeldt.</p>

    <h3>Tilmelding til kurser</h3>
    <p>I kan nu tilmelde jer kurser på to måder:</p>

    <ol>
        <li><strong>Via direkte link:</strong><br>
            <a href="{signup_url}">{signup_url}</a></li>
        <li><strong>Via kode:</strong><br>
            Gå til {settings.SITE_URL}/signup/course/ og indtast koden: <strong>{school.signup_password}</strong></li>
    </ol>

    <p>Med venlig hilsen,<br>Basal</p>
    """

    if not getattr(settings, "RESEND_API_KEY", None):
        logger.info(f"[EMAIL] To: {contact_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body: {body_html[:200]}...")
        return True

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send(
            {
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [contact_email],
                "subject": subject,
                "html": body_html,
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send enrollment confirmation: {e}")
        return False


def send_school_signup_notifications(school, contact_name, contact_email):
    """
    Send notification emails to staff users who opted in.

    Args:
        school: School instance that signed up
        contact_name: Name of school contact person
        contact_email: Email of school contact person

    Returns:
        Number of notifications sent
    """
    from apps.accounts.models import UserProfile

    # Get users with notification enabled
    subscribed_profiles = (
        UserProfile.objects.filter(notify_on_school_signup=True, user__email__isnull=False)
        .exclude(user__email="")
        .select_related("user")
    )

    if not subscribed_profiles:
        return 0

    subject = f"Ny skoletilmelding: {school.name}"
    school_url = f"{settings.SITE_URL}/schools/{school.pk}/"

    body_html = f"""
    <p>En ny skole har tilmeldt sig Basal:</p>

    <ul>
        <li><strong>Skole:</strong> {school.name}</li>
        <li><strong>Kommune:</strong> {school.kommune}</li>
        <li><strong>Kontaktperson:</strong> {contact_name} ({contact_email})</li>
    </ul>

    <p><a href="{school_url}">Se skolen i Basal</a></p>
    """

    count = 0
    for profile in subscribed_profiles:
        if not getattr(settings, "RESEND_API_KEY", None):
            logger.info(f"[EMAIL] Notification to: {profile.user.email}")
            logger.info(f"[EMAIL] Subject: {subject}")
            count += 1
            continue

        try:
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send(
                {
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [profile.user.email],
                    "subject": subject,
                    "html": body_html,
                }
            )
            count += 1
        except Exception as e:
            logger.error(f"Failed to send notification to {profile.user.email}: {e}")

    return count
