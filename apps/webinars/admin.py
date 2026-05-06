from django.contrib import admin
from django.utils.html import format_html

from .models import Webinar, WebinarSignUp


class WebinarSignUpInline(admin.TabularInline):
    model = WebinarSignUp
    extra = 0
    fields = ["participant_name", "participant_email", "kommune", "school_name", "created_at"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["kommune"]


@admin.register(Webinar)
class WebinarAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "start_at",
        "is_published",
        "signup_count",
        "capacity",
        "public_link",
    ]
    list_filter = ["is_published"]
    search_fields = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ["instructors"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [WebinarSignUpInline]

    @admin.display(description="Tilmeldingsside")
    def public_link(self, obj):
        if not obj.pk or not obj.is_published:
            return "—"
        url = obj.get_absolute_url()
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)


@admin.register(WebinarSignUp)
class WebinarSignUpAdmin(admin.ModelAdmin):
    list_display = [
        "participant_name",
        "participant_email",
        "webinar",
        "kommune",
        "school_name",
        "created_at",
    ]
    list_filter = ["webinar", "kommune"]
    search_fields = ["participant_name", "participant_email", "school_name"]
    raw_id_fields = ["webinar", "kommune"]
    readonly_fields = ["created_at", "email_bounced_at"]
