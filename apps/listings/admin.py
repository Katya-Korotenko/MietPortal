from django.contrib import admin
from django.utils.html import format_html

from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', 'district', 'price', 'rooms', 'property_type', 'is_active', 'deleted_status', 'created_at')
    list_filter = ('property_type', 'is_active', 'is_deleted', 'city')
    search_fields = ('title', 'city', 'district')

    def get_queryset(self, request):
        return Listing.all_objects.all()

    def deleted_status(self, obj):
        if obj.is_deleted:
            return format_html('<span style="color: {}; font-weight: bold;">{}</span>', 'red', '🗑 Deleted')
        return format_html('<span style="color: {};">{}</span>', 'green', 'Active')

    deleted_status.short_description = 'Status'