from django.contrib import admin

from .models import Course, CourseSignUp


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'datetime', 'location', 'capacity', 'signup_count', 'is_published']
    list_filter = ['is_published', 'datetime']
    search_fields = ['title', 'location']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CourseSignUp)
class CourseSignUpAdmin(admin.ModelAdmin):
    list_display = ['participant_name', 'school', 'course', 'attendance', 'created_at']
    list_filter = ['attendance', 'course', 'created_at']
    search_fields = ['participant_name', 'school__name', 'course__title']
    raw_id_fields = ['school', 'course']
