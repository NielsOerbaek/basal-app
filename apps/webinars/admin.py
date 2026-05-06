from django import forms
from django.contrib import admin

from .models import Webinar, WebinarSignUp


class WebinarAdminForm(forms.ModelForm):
    class Meta:
        model = Webinar
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_published") and not cleaned.get("meeting_url"):
            raise forms.ValidationError({"meeting_url": "Mødelink skal udfyldes før webinaret kan offentliggøres."})
        return cleaned


class WebinarSignUpInline(admin.TabularInline):
    model = WebinarSignUp
    extra = 0
    fields = ["participant_name", "participant_email", "school", "organization", "created_at"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["school"]


@admin.register(Webinar)
class WebinarAdmin(admin.ModelAdmin):
    form = WebinarAdminForm
    list_display = [
        "title",
        "start_at",
        "access_mode",
        "is_published",
        "signup_count",
        "capacity",
    ]
    list_filter = ["access_mode", "is_published"]
    search_fields = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ["instructors"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [WebinarSignUpInline]


@admin.register(WebinarSignUp)
class WebinarSignUpAdmin(admin.ModelAdmin):
    list_display = [
        "participant_name",
        "participant_email",
        "webinar",
        "school",
        "organization",
        "created_at",
    ]
    list_filter = ["webinar", "school"]
    search_fields = ["participant_name", "participant_email", "organization"]
    raw_id_fields = ["school", "webinar"]
    readonly_fields = ["created_at", "email_bounced_at"]
