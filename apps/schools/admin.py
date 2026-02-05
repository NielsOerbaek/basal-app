from django.contrib import admin

from .models import Invoice, Person, School, SchoolComment


class PersonInline(admin.TabularInline):
    model = Person
    extra = 0
    fields = ["name", "titel", "phone", "email", "is_koordinator", "is_oekonomisk_ansvarlig"]


class SchoolCommentInline(admin.TabularInline):
    model = SchoolComment
    extra = 0
    fields = ["comment", "created_by", "created_at"]
    readonly_fields = ["created_at"]


class InvoiceInline(admin.TabularInline):
    model = Invoice
    extra = 0
    fields = ["invoice_number", "amount", "status", "date", "comment"]


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ["name", "kommune", "enrolled_at", "total_seats", "remaining_seats", "is_active"]
    list_filter = ["is_active", "enrolled_at", "created_at", "kommune"]
    search_fields = ["name", "adresse", "kommune"]
    readonly_fields = ["created_at", "updated_at", "total_seats", "remaining_seats"]
    inlines = [PersonInline, SchoolCommentInline, InvoiceInline]

    def total_seats(self, obj):
        return obj.total_seats

    total_seats.short_description = "Pladser i alt"

    def remaining_seats(self, obj):
        return obj.remaining_seats

    remaining_seats.short_description = "Ubrugte pladser"


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["name", "school", "titel", "email", "phone", "is_koordinator", "is_oekonomisk_ansvarlig"]
    list_filter = ["is_koordinator", "is_oekonomisk_ansvarlig"]
    search_fields = ["name", "email", "school__name"]
    raw_id_fields = ["school"]


@admin.register(SchoolComment)
class SchoolCommentAdmin(admin.ModelAdmin):
    list_display = ["school", "created_by", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["school__name", "comment"]
    raw_id_fields = ["school", "created_by"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "school", "amount", "status", "date"]
    list_filter = ["status", "date"]
    search_fields = ["invoice_number", "school__name", "comment"]
    raw_id_fields = ["school"]
