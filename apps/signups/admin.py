from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from apps.core.decorators import can_manage_signups

from .models import SeatInfoContent, SignupFormField, SignupPage


class SignupAdminMixin:
    """Mixin to allow Tilmeldingsadministrator group to manage signup models."""

    def has_module_permission(self, request):
        if can_manage_signups(request.user):
            return True
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        if can_manage_signups(request.user):
            return True
        return super().has_view_permission(request, obj)

    def has_add_permission(self, request, obj=None):
        if can_manage_signups(request.user):
            return True
        # Handle both ModelAdmin (no obj) and InlineModelAdmin (with obj) signatures
        if obj is None:
            return super().has_add_permission(request)
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if can_manage_signups(request.user):
            return True
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if can_manage_signups(request.user):
            return True
        return super().has_delete_permission(request, obj)


class SignupFormFieldInline(SignupAdminMixin, admin.TabularInline):
    model = SignupFormField
    extra = 0
    fields = ["field_type", "label", "help_text", "is_required", "attachment", "order"]
    ordering = ["order", "id"]


@admin.register(SignupPage)
class SignupPageAdmin(SignupAdminMixin, SummernoteModelAdmin):
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
class SignupFormFieldAdmin(SignupAdminMixin, admin.ModelAdmin):
    list_display = ["label", "signup_page", "field_type", "is_required", "order"]
    list_filter = ["signup_page", "field_type", "is_required"]
    search_fields = ["label", "help_text"]
    ordering = ["signup_page", "order", "id"]


@admin.register(SeatInfoContent)
class SeatInfoContentAdmin(SignupAdminMixin, SummernoteModelAdmin):
    list_display = ["scenario", "title", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]
    summernote_fields = ["content"]

    fieldsets = [
        (None, {"fields": ["scenario", "title", "content"]}),
        ("Metadata", {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]
