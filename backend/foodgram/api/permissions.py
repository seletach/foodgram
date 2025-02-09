from rest_framework import permissions


class OwnerOrReadOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return (request.method in permissions.SAFE_METHODS
                or obj.author == request.user)


class IsOwnerOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.author == request.user


class DenyAllPermission(permissions.BasePermission):
    """
    Permission class that denies all requests.
    """

    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False
