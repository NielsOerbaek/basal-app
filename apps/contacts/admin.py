from django.contrib import admin

from .models import ContactTime


@admin.register(ContactTime)
class ContactTimeAdmin(admin.ModelAdmin):
    list_display = ['school', 'created_by', 'contacted_date', 'contacted_time', 'inbound', 'created_at']
    list_filter = ['contacted_date', 'inbound', 'created_by']
    search_fields = ['school__name', 'comment']
    raw_id_fields = ['school', 'created_by']
    readonly_fields = ['created_at']
