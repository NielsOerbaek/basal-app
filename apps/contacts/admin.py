from django.contrib import admin

from .models import ContactTime


@admin.register(ContactTime)
class ContactTimeAdmin(admin.ModelAdmin):
    list_display = ['school', 'employee', 'contacted_at', 'created_at']
    list_filter = ['contacted_at', 'employee']
    search_fields = ['school__name', 'comment']
    raw_id_fields = ['school', 'employee']
    readonly_fields = ['created_at']
