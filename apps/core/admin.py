from django.contrib import admin

from .models import ProjectSettings


@admin.register(ProjectSettings)
class ProjectSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            "Beregningsindstillinger",
            {
                "fields": ["klasseforloeb_per_teacher_per_year", "students_per_klasseforloeb"],
            },
        ),
        (
            "Skolernes side (vises på alle tilmeldte skoler)",
            {
                "fields": ["samarbejdsvilkaar_file", "login_info_text"],
            },
        ),
    ]

    def has_add_permission(self, request):
        # Singleton — only allow adding if none exists
        return not ProjectSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
