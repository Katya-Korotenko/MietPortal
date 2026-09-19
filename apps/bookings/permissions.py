from rest_framework import permissions


class IsBookingTenant(permissions.BasePermission):
    """Object-level check: only the tenant who made this specific booking may act on it."""

    def has_object_permission(self, request, view, obj):
        return obj.tenant == request.user


class IsBookingLandlord(permissions.BasePermission):
    """Object-level check: only the landlord of the listing this booking belongs to may act on it."""

    def has_object_permission(self, request, view, obj):
        return obj.listing.landlord == request.user