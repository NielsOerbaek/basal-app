from django.contrib import admin

from .models import Course, CourseSignUp, Instructor, Location


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "street_address", "postal_code", "municipality", "created_at"]
    search_fields = ["name", "street_address", "municipality"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["display_name", "start_date", "end_date", "location", "capacity", "signup_count", "is_published"]
    list_filter = ["is_published", "start_date"]
    search_fields = ["location__name"]
    readonly_fields = ["created_at", "updated_at"]
    filter_horizontal = ["instructors"]


@admin.register(CourseSignUp)
class CourseSignUpAdmin(admin.ModelAdmin):
    list_display = ["participant_name", "school", "course", "attendance", "created_at"]
    list_filter = ["attendance", "course", "created_at"]
    search_fields = ["participant_name", "school__name"]
    raw_id_fields = ["school", "course"]
