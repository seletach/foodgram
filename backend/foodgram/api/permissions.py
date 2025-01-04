# class BasePermission(metaclass=BasePermissionMetaclass):

#     # Определяет права на уровне запроса и пользователя
#     def has_permission(self, request, view):
#         return True

#     # Определяет права на уровне объекта
#     def has_object_permission(self, request, view, obj):
#         return True 

from rest_framework import permissions


class OwnerOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return (
                request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated
            )

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user
    

class IsOwnerOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user