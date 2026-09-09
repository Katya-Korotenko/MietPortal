from rest_framework import permissions


class IsBookingTenant(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.tenant == request.user


class IsBookingLandlord(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.listing.landlord == request.user