from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('booking', 'get_tenant', 'get_listing', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('booking__tenant__username', 'booking__listing__title', 'comment')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('booking',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('booking__tenant', 'booking__listing')

    def get_tenant(self, obj):
        return obj.booking.tenant.username
    get_tenant.short_description = 'Tenant'

    def get_listing(self, obj):
        return obj.booking.listing.title
    get_listing.short_description = 'Listing'