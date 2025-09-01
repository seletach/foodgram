from rest_framework.permissions import BasePermission


class IsRecipeAuthor(BasePermission):
    """Только автор может удалять удалять или изменять рецепт."""

    def has_object_permission(self, request, view, obj):
        """Проверка, является ли пользователь автором рецепта."""
        return obj.author == request.user
