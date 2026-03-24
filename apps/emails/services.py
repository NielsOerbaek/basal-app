import logging
import re

import resend
from django.conf import settings
from django.template import Context, Template
from django.utils.formats import date_format
from django.utils.safestring import mark_safe

from .models import EmailLog, EmailTemplate, EmailType

logger = logging.getLogger(__name__)


def check_email_domain_allowed(email):
    """
    Check if the recipient email domain is in the allowlist.
    Returns True if allowed (or if no allowlist is configured).
    """
    allowed = settings.EMAIL_ALLOWED_DOMAINS
    if not allowed:
        return True
    domain = email.rsplit("@", 1)[-1].lower()
    return domain in [d.lower() for d in allowed]


DEFAULT_REPLY_TO = ["basal@sundkom.dk"]


def auto_link_urls(html):
    """Turn plain-text URLs into clickable links, skipping URLs already inside an <a> tag."""
    import re

    return re.sub(
        r'(?<!["\'>=/])(https?://[^\s<>"\']+)',
        r'<a href="\1">\1</a>',
        html,
    )


def make_urls_absolute(html):
    """Convert relative src/href URLs to absolute using SITE_URL."""
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        return html
    html = re.sub(r'(src|href)="(/[^"]+)"', rf'\1="{site_url}\2"', html)
    return html


def render_template(template_string, context_dict):
    """Render a template string with the given context."""
    template = Template(template_string)
    context = Context(context_dict)
    return make_urls_absolute(auto_link_urls(template.render(context)))


def get_signup_context(signup):
    """Build template context from a CourseSignUp instance."""
    course = signup.course
    return {
        "participant_name": signup.participant_name,
        "participant_email": signup.participant_email,
        "participant_title": signup.participant_title,
        "school_name": signup.school.name,
        "course_title": course.display_name,
        "course_date": date_format(course.start_date, "j. F Y"),
        "course_end_date": date_format(course.end_date, "j. F Y"),
        "course_location": course.location.full_address if course.location else "",
        "instructors": ", ".join(course.instructors.values_list("name", flat=True)),
        "registration_deadline": date_format(course.registration_deadline, "j. F Y")
        if course.registration_deadline
        else "",
        "spots_remaining": course.spots_remaining,
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

    # Enforce email domain allowlist
    if not check_email_domain_allowed(signup.participant_email):
        logger.warning(
            f"[EMAIL BLOCKED] Recipient {signup.participant_email} not in allowed domains: "
            f"{settings.EMAIL_ALLOWED_DOMAINS}"
        )
        EmailLog.objects.create(
            email_type=email_type,
            recipient_email=signup.participant_email,
            recipient_name=signup.participant_name,
            subject=subject,
            course=signup.course,
            signup=signup,
            success=False,
            error_message=f"[BLOCKED] Domain not in EMAIL_ALLOWED_DOMAINS: {settings.EMAIL_ALLOWED_DOMAINS}",
        )
        return False

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
            "reply_to": DEFAULT_REPLY_TO,
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


def _cumulative_seat_price(n):
    """Calculate cumulative price for n paid course seats (volume discount per school year)."""
    if n <= 0:
        return 0
    if n == 1:
        return 7995
    if n == 2:
        return 15190
    if n == 3:
        return 21586
    return 21586 + (n - 3) * 7195


def send_course_signup_notification(school, course, signups):
    """
    Send notification email to admin when a school signs up for a course.

    Args:
        school: School instance
        course: Course instance
        signups: list of CourseSignUp instances created in this submission
    """
    notification_email = getattr(settings, "COURSE_SIGNUP_NOTIFICATION_EMAIL", "basal@sundkom.dk")

    oeko = school.people.filter(is_oekonomisk_ansvarlig=True).first()
    oeko_name = oeko.name if oeko else "–"

    # Calculate billing: signups are already saved, so derive "before" state
    n_new = len(signups)
    seat_info = school.seats_for_course(course)
    free_seats = seat_info["free"]
    used_after = seat_info["used"]
    used_before = used_after - n_new

    paid_before = max(0, used_before - free_seats)
    paid_after = max(0, used_after - free_seats)
    paid_this = paid_after - paid_before
    free_this = n_new - paid_this

    invoice_amount = _cumulative_seat_price(paid_after) - _cumulative_seat_price(paid_before)

    if paid_this > 0:
        billing_html = f"<li><strong>Fakturering:</strong> {paid_this} tilkøbt plads{'er' if paid_this != 1 else ''} – <strong>{invoice_amount:,} kr.</strong></li>"
    else:
        billing_html = f"<li><strong>Fakturering:</strong> Gratis ({free_this} inkluderet plads{'er' if free_this != 1 else ''})</li>"

    participants_html = "".join(f"<li>{s.participant_name} ({s.participant_email})</li>" for s in signups)

    body_html = f"""
<p><strong>Ny kursustilmelding</strong></p>
<ul>
  <li><strong>Skole:</strong> {school.name}</li>
  <li><strong>Kursus:</strong> {course.display_name}</li>
  <li><strong>Deltagere:</strong>
    <ul>{participants_html}</ul>
  </li>
  <li><strong>Økonomisk ansvarlig:</strong> {oeko_name}</li>
  <li><strong>EAN/CVR-nummer:</strong> {school.ean_nummer or "–"}</li>
  {billing_html}
</ul>
"""

    if not getattr(settings, "RESEND_API_KEY", None):
        logger.info(f"[EMAIL] To: {notification_email}")
        logger.info(f"[EMAIL] Subject: Ny kursustilmelding – {school.name}")
        logger.info(f"[EMAIL] Body: {body_html[:200]}...")
        return True

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send(
            {
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [notification_email],
                "reply_to": DEFAULT_REPLY_TO,
                "subject": f"Ny kursustilmelding – {school.name}",
                "html": body_html,
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send course signup notification: {e}")
        return False


def get_school_enrollment_context(school, contact_name):
    """Build template context for school enrollment confirmation."""
    return {
        "contact_name": contact_name,
        "school_name": school.name,
        "school_page_url": f"{settings.SITE_URL}/school/{school.signup_token}/",
        "signup_url": f"{settings.SITE_URL}/signup/course/?token={school.signup_token}",
        "signup_password": school.signup_password,
        "site_url": settings.SITE_URL,
        "school_address": school.adresse,
        "school_municipality": school.kommune,
        "ean_nummer": school.ean_nummer or "",
    }


def send_school_enrollment_confirmation(school, contact_email, contact_name, attachments=None):
    """
    Send enrollment confirmation email to school contact using EmailTemplate.

    Args:
        school: School instance with credentials
        contact_email: Email address of contact person
        contact_name: Name of contact person
        attachments: Optional list of dicts with 'filename', 'content' (bytes)

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
    body_html = render_template(template.body_html, context)

    # Enforce email domain allowlist
    if not check_email_domain_allowed(contact_email):
        logger.warning(
            f"[EMAIL BLOCKED] Recipient {contact_email} not in allowed domains: " f"{settings.EMAIL_ALLOWED_DOMAINS}"
        )
        return False

    bcc_email = getattr(settings, "SCHOOL_SIGNUP_BCC_EMAIL", "niels@osogdata.dk")

    if not getattr(settings, "RESEND_API_KEY", None):
        logger.info(f"[EMAIL] To: {contact_email}")
        logger.info(f"[EMAIL] BCC: {bcc_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body: {body_html[:200]}...")
        if attachments:
            logger.info(f"[EMAIL] Attachments: {[a['filename'] for a in attachments]}")
        return True

    try:
        resend.api_key = settings.RESEND_API_KEY
        email_params = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [contact_email],
            "bcc": [bcc_email],
            "reply_to": DEFAULT_REPLY_TO,
            "subject": subject,
            "html": body_html,
        }
        if attachments:
            email_params["attachments"] = attachments
        resend.Emails.send(email_params)
        return True
    except Exception as e:
        logger.error(f"Failed to send enrollment confirmation: {e}")
        return False


def get_coordinator_signup_context(coordinator, course, signups):
    """Build template context for coordinator signup confirmation."""
    participants_html = (
        "<ul>" + "".join(f"<li>{s.participant_name} ({s.participant_email})</li>" for s in signups) + "</ul>"
    )
    return {
        "coordinator_name": coordinator.name if coordinator else "Koordinator",
        "course_title": course.display_name,
        "course_date": date_format(course.start_date, "j. F Y"),
        "course_end_date": date_format(course.end_date, "j. F Y"),
        "course_location": course.location.full_address if course.location else "",
        "school_name": signups[0].school.name if signups else "",
        "participants_list": mark_safe(participants_html),
        "registration_deadline": date_format(course.registration_deadline, "j. F Y")
        if course.registration_deadline
        else "",
        "instructors": ", ".join(course.instructors.values_list("name", flat=True)),
    }


def send_coordinator_signup_confirmation(school, course, signups, override_email=None):
    """
    Send signup confirmation to the school's coordinator.

    Args:
        school: School instance
        course: Course instance
        signups: list of CourseSignUp instances from this batch
        override_email: optional email to send to instead of coordinator

    Returns:
        True if successful, False otherwise
    """
    coordinator = school.people.filter(is_koordinator=True).first()

    # Determine recipient
    if override_email:
        recipient_email = override_email
        recipient_name = coordinator.name if coordinator else "Koordinator"
    elif coordinator and coordinator.email:
        recipient_email = coordinator.email
        recipient_name = coordinator.name
    else:
        logger.warning(f"No coordinator email for school {school.name} — skipping coordinator notification")
        return False

    try:
        template = EmailTemplate.objects.get(email_type=EmailType.COORDINATOR_SIGNUP, is_active=True)
    except EmailTemplate.DoesNotExist:
        logger.warning("No active template found for coordinator signup confirmation")
        return False

    context = get_coordinator_signup_context(coordinator, course, signups)
    subject = render_template(template.subject, context)
    body_html = render_template(template.body_html, context)

    # Enforce email domain allowlist
    if not check_email_domain_allowed(recipient_email):
        logger.warning(
            f"[EMAIL BLOCKED] Recipient {recipient_email} not in allowed domains: " f"{settings.EMAIL_ALLOWED_DOMAINS}"
        )
        EmailLog.objects.create(
            email_type=EmailType.COORDINATOR_SIGNUP,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            course=course,
            success=False,
            error_message=f"[BLOCKED] Domain not in EMAIL_ALLOWED_DOMAINS: {settings.EMAIL_ALLOWED_DOMAINS}",
        )
        return False

    if not settings.RESEND_API_KEY:
        logger.info(f"[EMAIL] To: {recipient_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body: {body_html[:200]}...")
        EmailLog.objects.create(
            email_type=EmailType.COORDINATOR_SIGNUP,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            course=course,
            success=True,
            error_message="[DEV MODE - not actually sent]",
        )
        return True

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send(
            {
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [recipient_email],
                "reply_to": DEFAULT_REPLY_TO,
                "subject": subject,
                "html": body_html,
            }
        )
        EmailLog.objects.create(
            email_type=EmailType.COORDINATOR_SIGNUP,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            course=course,
            success=True,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send coordinator signup confirmation: {e}")
        EmailLog.objects.create(
            email_type=EmailType.COORDINATOR_SIGNUP,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            course=course,
            success=False,
            error_message=str(e),
        )
        return False
