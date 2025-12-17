from django.contrib import admin

from .models import School, SeatPurchase, Person, SchoolComment


class SeatPurchaseInline(admin.TabularInline):
    model = SeatPurchase
    extra = 0
    fields = ['seats', 'purchased_at', 'notes']


class PersonInline(admin.TabularInline):
    model = Person
    extra = 0
    fields = ['name', 'role', 'role_other', 'phone', 'email', 'is_primary']


class SchoolCommentInline(admin.TabularInline):
    model = SchoolComment
    extra = 0
    fields = ['comment', 'created_by', 'created_at']
    readonly_fields = ['created_at']


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'kommune', 'enrolled_at', 'total_seats', 'remaining_seats', 'is_active']
    list_filter = ['is_active', 'enrolled_at', 'created_at', 'kommune']
    search_fields = ['name', 'adresse', 'kommune']
    readonly_fields = ['created_at', 'updated_at', 'total_seats', 'remaining_seats']
    inlines = [PersonInline, SchoolCommentInline, SeatPurchaseInline]

    def total_seats(self, obj):
        return obj.total_seats
    total_seats.short_description = 'Pladser i alt'

    def remaining_seats(self, obj):
        return obj.remaining_seats
    remaining_seats.short_description = 'Ubrugte pladser'


@admin.register(SeatPurchase)
class SeatPurchaseAdmin(admin.ModelAdmin):
    list_display = ['school', 'seats', 'purchased_at', 'created_at']
    list_filter = ['purchased_at']
    search_fields = ['school__name', 'notes']
    raw_id_fields = ['school']


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['name', 'school', 'role', 'email', 'phone', 'is_primary']
    list_filter = ['role', 'is_primary']
    search_fields = ['name', 'email', 'school__name']
    raw_id_fields = ['school']


@admin.register(SchoolComment)
class SchoolCommentAdmin(admin.ModelAdmin):
    list_display = ['school', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['school__name', 'comment']
    raw_id_fields = ['school', 'created_by']
