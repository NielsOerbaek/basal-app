from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"

    def ready(self):
        from apps.audit import signals  # noqa
        from apps.audit.registry import register_for_audit, AuditConfig as AuditCfg

        from apps.schools.models import School, SeatPurchase, Person, SchoolComment, Invoice, SchoolYear
        from apps.courses.models import Course, CourseSignUp, CourseMaterial
        from apps.contacts.models import ContactTime
        from apps.signups.models import SignupPage, SignupFormField

        # School and related models
        register_for_audit(
            School,
            AuditCfg(
                get_school=lambda instance: instance,
            ),
        )

        register_for_audit(
            SeatPurchase,
            AuditCfg(
                get_school=lambda instance: instance.school,
            ),
        )

        register_for_audit(
            Person,
            AuditCfg(
                get_school=lambda instance: instance.school,
            ),
        )

        register_for_audit(
            SchoolComment,
            AuditCfg(
                excluded_fields=["id", "created_at", "created_by"],
                get_school=lambda instance: instance.school,
            ),
        )

        register_for_audit(
            Invoice,
            AuditCfg(
                get_school=lambda instance: instance.school,
            ),
        )

        register_for_audit(
            Course,
            AuditCfg(
                get_course=lambda instance: instance,
            ),
        )

        register_for_audit(
            CourseSignUp,
            AuditCfg(
                get_school=lambda instance: instance.school,
                get_course=lambda instance: instance.course,
            ),
        )

        register_for_audit(
            ContactTime,
            AuditCfg(
                excluded_fields=["id", "created_at", "created_by"],
                get_school=lambda instance: instance.school,
            ),
        )

        # School year tracking
        register_for_audit(SchoolYear, AuditCfg())

        # Course materials
        register_for_audit(
            CourseMaterial,
            AuditCfg(
                get_course=lambda instance: instance.course,
            ),
        )

        # Signups app
        register_for_audit(SignupPage, AuditCfg())

        register_for_audit(SignupFormField, AuditCfg())
