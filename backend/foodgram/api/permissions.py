from rest_framework import permissions
from djoser.permissions import CurrentUserOrAdmin
from rest_framework.permissions import SAFE_METHODS


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


class IsAuthenticatedOrAuthorOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated or request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.author == request.user


class OwnerOrAdminOrReadOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
            or request.user.is_authenticated and request.user.is_admin
        ):
            return True
