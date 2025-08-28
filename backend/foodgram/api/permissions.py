from rest_framework.permissions import BasePermission


class IsRecipeAuthor(BasePermission):
    """Разрешение, позволяющее только автору рецепта редактировать или удалять его."""

    def has_object_permission(self, request, view, obj):
        """Проверка, является ли пользователь автором рецепта."""
        return obj.author == request.user
