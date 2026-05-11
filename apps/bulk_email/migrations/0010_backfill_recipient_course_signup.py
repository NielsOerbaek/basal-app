"""Backfill course_signup on legacy underviser-type recipients.

Past UNDERVISERE_KURSUS recipients were stored with person=NULL because the
participant came from a CourseSignUp rather than a saved Person. Match them
back to the originating CourseSignUp by school + email (case-insensitive) so
the detail view can display participant name/role instead of "Person slettet".
"""

from django.db import migrations


def backfill_course_signup(apps, schema_editor):
    BulkEmail = apps.get_model("bulk_email", "BulkEmail")
    BulkEmailRecipient = apps.get_model("bulk_email", "BulkEmailRecipient")
    CourseSignUp = apps.get_model("courses", "CourseSignUp")

    UNDERVISERE_KURSUS = "undervisere_kursus"

    # JSONField __contains isn't supported on SQLite — filter in Python instead.
    # The campaign table is small (one row per send), so this is fine.
    campaign_ids = [
        pk
        for pk, types in BulkEmail.objects.values_list("pk", "recipient_types")
        if isinstance(types, list) and UNDERVISERE_KURSUS in types
    ]
    if not campaign_ids:
        return

    orphan_recipients = list(
        BulkEmailRecipient.objects.filter(
            bulk_email_id__in=campaign_ids,
            person__isnull=True,
            course_signup__isnull=True,
            school__isnull=False,
        )
    )
    if not orphan_recipients:
        return

    # Build lookup: (school_id, email.lower()) -> CourseSignUp.pk (prefer is_underviser=True)
    keys = {(r.school_id, r.email.lower()) for r in orphan_recipients}
    school_ids = {r.school_id for r in orphan_recipients}
    signup_map = {}
    for su in (
        CourseSignUp.objects.filter(school_id__in=school_ids)
        .exclude(participant_email="")
        # Lower-priority rows first so is_underviser=True overwrites them last.
        .order_by("is_underviser")
    ):
        key = (su.school_id, su.participant_email.lower())
        if key in keys:
            signup_map[key] = su.pk

    for r in orphan_recipients:
        signup_pk = signup_map.get((r.school_id, r.email.lower()))
        if signup_pk:
            r.course_signup_id = signup_pk
            r.save(update_fields=["course_signup"])


class Migration(migrations.Migration):
    dependencies = [
        ("bulk_email", "0009_add_course_signup_fk"),
        ("courses", "0021_coursesignup_affiliation_xor"),
    ]

    operations = [
        migrations.RunPython(backfill_course_signup, migrations.RunPython.noop),
    ]
