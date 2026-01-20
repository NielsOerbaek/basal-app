from django.contrib import admin
from django.utils import timezone
from django_summernote.admin import SummernoteModelAdmin

from .models import SchoolSignup, SignupFormField, SignupPage


class SignupFormFieldInline(admin.TabularInline):
    model = SignupFormField
    extra = 0
    fields = ["field_type", "label", "help_text", "is_required", "attachment", "order"]
    ordering = ["order", "id"]


@admin.register(SignupPage)
class SignupPageAdmin(SummernoteModelAdmin):
    list_display = ["page_type", "title", "is_active", "updated_at"]
    list_filter = ["is_active", "page_type"]
    search_fields = ["title", "subtitle"]
    readonly_fields = ["created_at", "updated_at"]

    summernote_fields = ["intro_text", "success_message"]

    fieldsets = [
        ("Sidetype", {"fields": ["page_type", "is_active"]}),
        ("Sideindhold", {"fields": ["title", "subtitle", "intro_text"]}),
        ("Successide", {"fields": ["success_title", "success_message"]}),
        ("Knap", {"fields": ["submit_button_text"]}),
        ("Metadata", {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]

    inlines = [SignupFormFieldInline]


@admin.register(SignupFormField)
class SignupFormFieldAdmin(admin.ModelAdmin):
    list_display = ["label", "signup_page", "field_type", "is_required", "order"]
    list_filter = ["signup_page", "field_type", "is_required"]
    search_fields = ["label", "help_text"]
    ordering = ["signup_page", "order", "id"]


@admin.register(SchoolSignup)
class SchoolSignupAdmin(admin.ModelAdmin):
    list_display = ["school_display_name", "municipality", "contact_name", "contact_email", "created_at", "processed"]
    list_filter = ["processed", "municipality", "created_at"]
    search_fields = ["school__name", "new_school_name", "contact_name", "contact_email", "municipality"]
    readonly_fields = ["created_at", "processed_at", "processed_by"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    fieldsets = [
        ("Skole", {"fields": ["school", "new_school_name", "municipality"]}),
        ("Kontaktperson", {"fields": ["contact_name", "contact_email", "contact_phone", "contact_title"]}),
        ("Yderligere", {"fields": ["comments"]}),
        ("Behandling", {"fields": ["processed", "processed_at", "processed_by", "created_at"]}),
    ]

    actions = ["mark_as_processed"]

    @admin.action(description="Marker som behandlet")
    def mark_as_processed(self, request, queryset):
        updated = queryset.filter(processed=False).update(
            processed=True, processed_at=timezone.now(), processed_by=request.user
        )
        self.message_user(request, f"{updated} tilmelding(er) markeret som behandlet.")

    def save_model(self, request, obj, form, change):
        if "processed" in form.changed_data and obj.processed and not obj.processed_at:
            obj.processed_at = timezone.now()
            obj.processed_by = request.user
        super().save_model(request, obj, form, change)
