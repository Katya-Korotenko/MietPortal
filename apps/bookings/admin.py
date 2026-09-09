from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(SimpleHistoryAdmin):
    list_display = ('listing', 'start_date', 'end_date', 'status', 'created_at')
    list_filter = ('status',)