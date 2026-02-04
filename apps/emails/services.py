import logging

import resend
from django.conf import settings
from django.template import Context, Template
from django.utils.formats import date_format

from .models import EmailLog, EmailTemplate, EmailType

logger = logging.getLogger(__name__)

EMAIL_FOOTER = """
<hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
<p style="color: #666; font-size: 12px;">
    Har du spørgsmål? Kontakt os på <a href="mailto:basal@sundkom.dk">basal@sundkom.dk</a>
</p>
"""


def add_email_footer(body_html):
    """Add standard footer to email body."""
    return body_html + EMAIL_FOOTER


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
        "course_title": signup.course.display_name,
        "course_date": date_format(signup.course.start_date, "j. F Y"),
        "course_location": signup.course.location.full_address if signup.course.location else "",
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
    body_html = add_email_footer(render_template(template.body_html, context))

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


def get_school_enrollment_context(school, contact_name):
    """Build template context for school enrollment confirmation."""
    return {
        "contact_name": contact_name,
        "school_name": school.name,
        "school_page_url": f"{settings.SITE_URL}/school/{school.signup_token}/",
        "signup_url": f"{settings.SITE_URL}/signup/course/?token={school.signup_token}",
        "signup_password": school.signup_password,
        "site_url": settings.SITE_URL,
    }


def send_school_enrollment_confirmation(school, contact_email, contact_name):
    """
    Send enrollment confirmation email to school contact using EmailTemplate.

    Args:
        school: School instance with credentials
        contact_email: Email address of contact person
        contact_name: Name of contact person

    Returns:
        True if successful, False otherwise
    """
    try:
        template = EmailTemplate.objects.get(email_type=EmailType.SCHOOL_ENROLLMENT_CONFIRMATION, is_active=True)
    except EmailTemplate.DoesNotExist:
        logger.warning("No active template found for school enrollment confirmation")
        return False

    context = get_school_enrollment_context(school, contact_name)
    subject = render_template(template.subject, context)
    body_html = add_email_footer(render_template(template.body_html, context))

    bcc_email = getattr(settings, "SCHOOL_SIGNUP_BCC_EMAIL", "basal@sundkom.dk")

    if not getattr(settings, "RESEND_API_KEY", None):
        logger.info(f"[EMAIL] To: {contact_email}")
        logger.info(f"[EMAIL] BCC: {bcc_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body: {body_html[:200]}...")
        return True

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send(
            {
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [contact_email],
                "bcc": [bcc_email],
                "subject": subject,
                "html": body_html,
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send enrollment confirmation: {e}")
        return False
