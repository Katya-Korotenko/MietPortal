from rest_framework import permissions


class IsLandlord(permissions.BasePermission):
    """Request-level check: does this user belong to the Landlord group at all?
    Does not check ownership of any specific object — see IsOwnerOrReadOnly
    for that."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_landlord)


class IsTenant(permissions.BasePermission):
    """Request-level check: does this user belong to the Tenant group at all?"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_tenant)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level check: anyone can read (GET/HEAD/OPTIONS), but only the
    object's own landlord can write to it. Assumes the object has a
    `landlord` field — currently only used by Listing.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.landlord == request.user