from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from core.constants import DEFAULT_CURRENCY
from .models import Booking


@admin.register(Booking)
class BookingAdmin(SimpleHistoryAdmin):
    """Renders the booking status as colored text for quick visual scanning in the admin list."""
    list_display = ('listing', 'tenant', 'start_date', 'end_date', 'total_price_display', 'status_display', 'created_at')
    list_filter = ('status', 'start_date', 'created_at')
    search_fields = ('listing__title', 'tenant__username', 'tenant__email')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('listing', 'tenant')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('listing', 'tenant')

    def total_price_display(self, obj):
        nights = (obj.end_date - obj.start_date).days
        return f'{obj.listing.price * nights} {DEFAULT_CURRENCY}'
    total_price_display.short_description = 'Total Price'

    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'confirmed': 'green',
            'rejected': 'red',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())
    status_display.short_description = 'Status'