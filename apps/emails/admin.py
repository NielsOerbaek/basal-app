from django.contrib import admin
from django.utils.safestring import mark_safe
from django_summernote.admin import SummernoteModelAdmin

from .models import EmailLog, EmailTemplate, EmailType


@admin.register(EmailTemplate)
class EmailTemplateAdmin(SummernoteModelAdmin):
    list_display = ["email_type", "subject", "is_active", "updated_at"]
    list_filter = ["is_active", "email_type"]
    search_fields = ["subject", "body_html"]
    readonly_fields = ["email_type", "description", "updated_at", "available_variables"]
    summernote_fields = ("body_html",)

    fieldsets = (
        (None, {"fields": ("email_type", "description", "is_active")}),
        (
            "Indhold",
            {
                "fields": ("subject", "body_html"),
                "description": 'Brug variabler i teksten — se "Tilgængelige variabler" nedenfor for den fulde liste.',
            },
        ),
        (
            "Tilgængelige variabler",
            {
                "fields": ("available_variables",),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("updated_at",),
                "classes": ("collapse",),
            },
        ),
    )

    VARIABLE_DISPLAY = {
        EmailType.SIGNUP_CONFIRMATION: [
            ("participant_name", "Deltagerens navn"),
            ("participant_email", "Deltagerens e-mail"),
            ("participant_title", "Deltagerens stilling"),
            ("school_name", "Skolens navn"),
            ("course_title", "Kursets titel"),
            ("course_date", "Kursets startdato"),
            ("course_end_date", "Kursets slutdato"),
            ("course_location", "Kursets lokation"),
            ("instructors", "Undervisere (kommasepareret)"),
            ("registration_deadline", "Tilmeldingsfrist"),
            ("spots_remaining", "Ledige pladser"),
        ],
        EmailType.COURSE_REMINDER: [
            ("participant_name", "Deltagerens navn"),
            ("participant_email", "Deltagerens e-mail"),
            ("participant_title", "Deltagerens stilling"),
            ("school_name", "Skolens navn"),
            ("course_title", "Kursets titel"),
            ("course_date", "Kursets startdato"),
            ("course_end_date", "Kursets slutdato"),
            ("course_location", "Kursets lokation"),
            ("instructors", "Undervisere (kommasepareret)"),
            ("registration_deadline", "Tilmeldingsfrist"),
            ("spots_remaining", "Ledige pladser"),
        ],
        EmailType.SCHOOL_ENROLLMENT_CONFIRMATION: [
            ("contact_name", "Kontaktpersonens navn"),
            ("school_name", "Skolens navn"),
            ("school_page_url", "Link til skolens side"),
            ("signup_url", "Link til kursustilmelding"),
            ("signup_password", "Skolens tilmeldingskode"),
            ("site_url", "Sidens URL"),
            ("school_address", "Skolens adresse"),
            ("school_municipality", "Kommune"),
            ("ean_nummer", "EAN/CVR-nummer"),
        ],
        EmailType.COORDINATOR_SIGNUP: [
            ("coordinator_name", "Koordinatorens navn"),
            ("course_title", "Kursets titel"),
            ("course_date", "Kursets startdato"),
            ("course_end_date", "Kursets slutdato"),
            ("course_location", "Kursets lokation"),
            ("school_name", "Skolens navn"),
            ("participants_list", "HTML-liste over tilmeldte deltagere"),
            ("registration_deadline", "Tilmeldingsfrist"),
            ("instructors", "Undervisere (kommasepareret)"),
        ],
    }

    def available_variables(self, obj):
        if not obj or not obj.email_type:
            return ""
        variables = self.VARIABLE_DISPLAY.get(obj.email_type, [])
        items = "".join(f"<li><code>{{{{ {name} }}}}</code> - {desc}</li>" for name, desc in variables)
        return mark_safe(f"<ul>{items}</ul>")

    available_variables.short_description = "Tilgængelige variabler"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["recipient_email", "email_type", "subject", "success", "sent_at"]
    list_filter = ["email_type", "success", "sent_at"]
    search_fields = ["recipient_email", "recipient_name", "subject"]
    readonly_fields = [
        "email_type",
        "recipient_email",
        "recipient_name",
        "subject",
        "course",
        "signup",
        "sent_at",
        "success",
        "error_message",
    ]
    date_hierarchy = "sent_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
