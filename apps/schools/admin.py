from django.contrib import admin

from .models import School, SeatPurchase


class SeatPurchaseInline(admin.TabularInline):
    model = SeatPurchase
    extra = 0
    fields = ['seats', 'purchased_at', 'notes']


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'contact_name', 'enrolled_at', 'total_seats', 'remaining_seats', 'is_active']
    list_filter = ['is_active', 'enrolled_at', 'created_at']
    search_fields = ['name', 'location', 'contact_name', 'contact_email']
    readonly_fields = ['created_at', 'updated_at', 'total_seats', 'remaining_seats']
    inlines = [SeatPurchaseInline]

    def total_seats(self, obj):
        return obj.total_seats
    total_seats.short_description = 'Pladser i alt'

    def remaining_seats(self, obj):
        return obj.remaining_seats
    remaining_seats.short_description = 'Ledige pladser'


@admin.register(SeatPurchase)
class SeatPurchaseAdmin(admin.ModelAdmin):
    list_display = ['school', 'seats', 'purchased_at', 'created_at']
    list_filter = ['purchased_at']
    search_fields = ['school__name', 'notes']
    raw_id_fields = ['school']
