from django.contrib import admin

from .models import ContactTime


@admin.register(ContactTime)
class ContactTimeAdmin(admin.ModelAdmin):
    list_display = ['school', 'created_by', 'contacted_at', 'created_at']
    list_filter = ['contacted_at', 'created_by']
    search_fields = ['school__name', 'comment']
    raw_id_fields = ['school', 'created_by']
    readonly_fields = ['created_at']
