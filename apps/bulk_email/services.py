import logging
import re
from datetime import date

import resend
from django.conf import settings
from django.template import Context, Template
from django.utils.formats import date_format

from apps.bulk_email.models import BulkEmail, BulkEmailRecipient
from apps.emails.services import DEFAULT_REPLY_TO, check_email_domain_allowed
from apps.schools.models import Person

logger = logging.getLogger(__name__)


def _to_date(value):
    """Coerce a string 'YYYY-MM-DD' or date object to a date object."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _billing_field(school, field):
    """Get a fakturering_* value, falling through to the kommune row if applicable."""
    val = getattr(school, field, "")
    if val:
        return val
    if school.kommunen_betaler and school.kommune_id:
        kommune = school.kommune
        if kommune:
            return getattr(kommune, field, "") or ""
    return ""


# All template variables and their source accessors
VARIABLE_ACCESSORS = {
    "skole_navn": lambda s, p: s.name,
    "adresse": lambda s, p: s.adresse,
    "postnummer": lambda s, p: s.postnummer,
    "by": lambda s, p: s.by,
    "kommune": lambda s, p: s.kommune.name if s.kommune else "",
    "ean_nummer": lambda s, p: s.ean_nummer,
    "fakturering_ean_nummer": lambda s, p: _billing_field(s, "fakturering_ean_nummer"),
    "fakturering_kontakt_navn": lambda s, p: _billing_field(s, "fakturering_kontakt_navn"),
    "fakturering_kontakt_email": lambda s, p: _billing_field(s, "fakturering_kontakt_email"),
    "tilmeldt_dato": lambda s, p: date_format(_to_date(s.enrolled_at), "j. F Y") if s.enrolled_at else "",
    "aktiv_fra": lambda s, p: date_format(_to_date(s.active_from), "j. F Y") if s.active_from else "",
    "kontakt_navn": lambda s, p: p.name if p else "",
    "kontakt_email": lambda s, p: p.email if p else "",
    "kontakt_telefon": lambda s, p: p.phone if p else "",
    "tilmeldings_link": lambda s, p: f"{settings.SITE_URL}/signup/course/?token={s.signup_token}"
    if s.signup_token
    else "",
    "skoleside_link": lambda s, p: f"{settings.SITE_URL}/school/{s.signup_token}/" if s.signup_token else "",
    "tilmeldings_adgangskode": lambda s, p: s.signup_password,
}

VARIABLE_NAMES = list(VARIABLE_ACCESSORS.keys())


def build_template_context(school, person):
    """Build the template rendering context dict for one school+person pair."""
    return {var: (accessor(school, person) or "") for var, accessor in VARIABLE_ACCESSORS.items()}


def make_urls_absolute(html):
    """Convert relative src/href URLs to absolute using SITE_URL."""
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        return html
    # Convert src="/media/..." and href="/media/..." etc. to absolute
    html = re.sub(r'(src|href)="(/[^"]+)"', rf'\1="{site_url}\2"', html)
    return html


def render_for_school(template_str, school, person):
    """Render a template string with school+person context."""
    ctx = build_template_context(school, person)
    return Template(template_str).render(Context(ctx))


def extract_variables_from_template(template_str):
    """Return list of variable names referenced in a template string."""
    return re.findall(r"\{\{\s*(\w+)\s*\}\}", template_str)


def find_missing_variables(template_str, school_person_pairs):
    """
    For each variable referenced in template_str, find schools where it resolves to blank.

    Returns:
        List of dicts: [{"variable": "{{ ean_nummer }}", "schools": ["Skole A", "Skole B"]}]
    """
    referenced = extract_variables_from_template(template_str)
    warnings = []
    for var in referenced:
        if var not in VARIABLE_ACCESSORS:
            continue
        accessor = VARIABLE_ACCESSORS[var]
        missing_schools = []
        for tup in school_person_pairs:
            school, person = tup[0], tup[1]
            value = accessor(school, person)
            if not value:
                missing_schools.append(school.name)
        if missing_schools:
            warnings.append({"variable": f"{{{{ {var} }}}}", "schools": missing_schools})
    return warnings


def resolve_recipients(schools, recipient_types):
    """
    For each school, find the matching contact person(s) across all selected types.

    Note: schools should have prefetch_related("people") applied for performance.

    Args:
        recipient_types: list of BulkEmail.RECIPIENT_TYPE_* values.

    Returns:
        List of (school, person, roles) triples where `roles` is a list of human-readable
        role labels (in the model's defined order) describing which selected types matched.
        Recipients are deduped per school by lowercase email — a person matching multiple
        types appears once with multiple role labels.

        For UNDERVISERE_KURSUS, person is an unsaved Person built from a CourseSignUp's
        participant fields (no pk — `send_to_school` handles this and stores the recipient
        with a null Person FK).
    """
    types = set(recipient_types or [])
    if not types:
        return []

    role_label = BulkEmail.RECIPIENT_ROLE_LABELS
    role_order = list(BulkEmail.RECIPIENT_ROLE_LABELS.keys())

    underviser_signups_by_school = {}
    if BulkEmail.UNDERVISERE_KURSUS in types:
        from apps.courses.models import CourseSignUp

        eligible_pks = [s.pk for s in schools if not s.do_not_contact_at]
        signups = (
            CourseSignUp.objects.filter(
                school_id__in=eligible_pks,
                is_underviser=True,
            )
            .exclude(participant_email="")
            .order_by("school_id", "participant_name")
        )
        for su in signups:
            underviser_signups_by_school.setdefault(su.school_id, []).append(su)

    result = []
    for school in schools:
        if school.do_not_contact_at:
            continue

        # candidates: dict keyed by email.lower() -> {"person": Person, "type_keys": set[str]}
        candidates = {}

        people_with_email = [p for p in school.people.all() if p.email]
        first_contact = people_with_email[0] if people_with_email else None

        for p in people_with_email:
            matched = []
            if BulkEmail.KOORDINATOR in types and p.is_koordinator:
                matched.append(BulkEmail.KOORDINATOR)
            if BulkEmail.OEKONOMISK_ANSVARLIG in types and p.is_oekonomisk_ansvarlig:
                matched.append(BulkEmail.OEKONOMISK_ANSVARLIG)
            if BulkEmail.FOERSTE_KONTAKT in types and p is first_contact:
                matched.append(BulkEmail.FOERSTE_KONTAKT)
            if BulkEmail.ALLE_KONTAKTER in types:
                matched.append(BulkEmail.ALLE_KONTAKTER)
            if not matched:
                continue
            key = p.email.lower()
            entry = candidates.setdefault(key, {"person": p, "type_keys": set()})
            entry["type_keys"].update(matched)

        for su in underviser_signups_by_school.get(school.pk, []):
            key = su.participant_email.lower()
            if key in candidates:
                candidates[key]["type_keys"].add(BulkEmail.UNDERVISERE_KURSUS)
            else:
                candidates[key] = {
                    "person": Person(
                        name=su.participant_name,
                        email=su.participant_email,
                        phone=su.participant_phone,
                    ),
                    "type_keys": {BulkEmail.UNDERVISERE_KURSUS},
                }

        for entry in candidates.values():
            roles = [role_label[t] for t in role_order if t in entry["type_keys"]]
            result.append((school, entry["person"], roles))

    return result


def send_to_school(bulk_email, school, person, attachment_data=None):
    """
    Send a single bulk email to one school/person. Writes and returns a BulkEmailRecipient.
    Does NOT abort on failure — caller should continue iterating.

    If attachment_data is provided (list of {"filename", "content"} dicts), it is used
    directly instead of re-reading files from disk — avoids repeated I/O in bulk loops.
    """
    email_address = person.email
    subject = render_for_school(bulk_email.subject, school, person)
    body_html = make_urls_absolute(render_for_school(bulk_email.body_html, school, person))

    recipient = BulkEmailRecipient(
        bulk_email=bulk_email,
        person=person if (person and person.pk) else None,
        school=school,
        email=email_address,
    )

    # Domain allowlist check
    if not check_email_domain_allowed(email_address):
        recipient.success = False
        recipient.error_message = "[BLOCKED] Domain not in EMAIL_ALLOWED_DOMAINS"
        recipient.save()
        return recipient

    # Dev mode guard
    if not getattr(settings, "RESEND_API_KEY", None):
        logger.info(f"[BULK EMAIL] DEV MODE — To: {email_address} Subject: {subject}")
        recipient.success = True
        recipient.error_message = "[DEV MODE - not actually sent]"
        recipient.save()
        return recipient

    try:
        resend.api_key = settings.RESEND_API_KEY
        if attachment_data is not None:
            attachments = attachment_data
        else:
            attachments = []
            for attachment in bulk_email.attachments.all():
                with attachment.file.open("rb") as f:
                    attachments.append({"filename": attachment.filename, "content": list(f.read())})

        params = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [email_address],
            "reply_to": DEFAULT_REPLY_TO,
            "subject": subject,
            "html": body_html,
        }
        if attachments:
            params["attachments"] = attachments

        result = resend.Emails.send(params)
        recipient.success = True
        if hasattr(result, "id"):
            recipient.resend_email_id = result.id
    except Exception as e:
        logger.error(f"[BULK EMAIL] Failed to send to {email_address}: {e}")
        recipient.success = False
        recipient.error_message = str(e)[:500]

    recipient.save()
    return recipient
