import logging

from django.conf import settings
from django.template import Template, Context
from django.utils.formats import date_format

import resend

from .models import EmailTemplate, EmailLog, EmailType

logger = logging.getLogger(__name__)


def render_template(template_string, context_dict):
    """Render a template string with the given context."""
    template = Template(template_string)
    context = Context(context_dict)
    return template.render(context)


def get_signup_context(signup):
    """Build template context from a CourseSignUp instance."""
    return {
        'participant_name': signup.participant_name,
        'participant_email': signup.participant_email,
        'participant_title': signup.participant_title,
        'school_name': signup.school.name,
        'course_title': signup.course.title,
        'course_date': date_format(signup.course.start_date, 'j. F Y'),
        'course_location': signup.course.location,
    }


def send_email(email_type, signup, extra_attachments=None):
    """
    Send an email using a template.

    Args:
        email_type: EmailType value
        signup: CourseSignUp instance
        extra_attachments: Optional list of dicts with 'filename', 'content' (bytes)

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

    # Build attachments list from template + any extra attachments
    attachments = []

    # Add template attachment if present
    if template.attachment:
        try:
            with template.attachment.open('rb') as f:
                attachments.append({
                    'filename': template.attachment.name.split('/')[-1],
                    'content': list(f.read()),
                })
        except Exception as e:
            logger.error(f"Failed to read template attachment: {e}")

    # Add any extra attachments (e.g., course-specific materials)
    if extra_attachments:
        attachments.extend(extra_attachments)

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
            error_message='[DEV MODE - not actually sent]'
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


def send_course_reminder(signup, extra_attachments=None):
    """Send course reminder email with optional extra attachments."""
    return send_email(EmailType.COURSE_REMINDER, signup, extra_attachments=extra_attachments)
