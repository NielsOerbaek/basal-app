from django.contrib import admin
from django.utils.html import format_html
from django_summernote.admin import SummernoteModelAdmin

from .models import EmailTemplate, EmailLog


@admin.register(EmailTemplate)
class EmailTemplateAdmin(SummernoteModelAdmin):
    list_display = ['email_type', 'subject', 'is_active', 'updated_at']
    list_filter = ['is_active', 'email_type']
    search_fields = ['subject', 'body_html']
    readonly_fields = ['updated_at', 'available_variables']
    summernote_fields = ('body_html',)

    fieldsets = (
        (None, {
            'fields': ('email_type', 'is_active')
        }),
        ('Indhold', {
            'fields': ('subject', 'body_html'),
            'description': 'Brug variabler som {{ participant_name }} i teksten'
        }),
        ('Vedhæftet fil', {
            'fields': ('attachment',),
            'description': 'Upload en PDF eller anden fil der sendes med alle e-mails af denne type'
        }),
        ('Tilgængelige variabler', {
            'fields': ('available_variables',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',),
        }),
    )

    def available_variables(self, obj):
        variables = """
        <ul>
            <li><code>{{ participant_name }}</code> - Deltagerens navn</li>
            <li><code>{{ participant_email }}</code> - Deltagerens e-mail</li>
            <li><code>{{ participant_title }}</code> - Deltagerens stilling</li>
            <li><code>{{ school_name }}</code> - Skolens navn</li>
            <li><code>{{ course_title }}</code> - Kursets titel</li>
            <li><code>{{ course_date }}</code> - Kursets startdato</li>
            <li><code>{{ course_location }}</code> - Kursets lokation</li>
        </ul>
        """
        return format_html(variables)
    available_variables.short_description = 'Tilgængelige variabler'


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'email_type', 'subject', 'success', 'sent_at']
    list_filter = ['email_type', 'success', 'sent_at']
    search_fields = ['recipient_email', 'recipient_name', 'subject']
    readonly_fields = [
        'email_type', 'recipient_email', 'recipient_name', 'subject',
        'course', 'signup', 'sent_at', 'success', 'error_message'
    ]
    date_hierarchy = 'sent_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
