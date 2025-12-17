from django.contrib import admin

from apps.audit.models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'content_type', 'object_repr', 'related_school']
    list_filter = ['action', 'content_type', 'timestamp']
    search_fields = ['object_repr', 'user__username']
    readonly_fields = [
        'user', 'content_type', 'object_id', 'object_repr',
        'action', 'changes', 'timestamp', 'related_school', 'related_course'
    ]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
