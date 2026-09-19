from rest_framework import permissions


class IsReviewOwner(permissions.BasePermission):
    """Object-level check: only the tenant who wrote this review may delete it."""

    def has_object_permission(self, request, view, obj):
        return obj.booking.tenant == request.user