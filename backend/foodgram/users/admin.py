from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import CustomUser, Subscription


@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin):
    """Пользователи."""

    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
        'subscribers_count',
        'recipes_count',
    )
    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_filter = ['is_staff']
    ordering = ['username']
    readonly_fields = ['date_joined', 'last_login']

    def subscribers_count(self, obj):
        """Количество подписчиков пользователя."""
        return obj.subscriber.count()
    subscribers_count.short_description = 'Подписчики'

    def recipes_count(self, obj):
        """Количество рецептов пользователя."""
        return obj.recipes.count()
    recipes_count.short_description = 'Рецепты'


@admin.register(Subscription)
class SubscriptionsAdmin(admin.ModelAdmin):
    """Подписки пользователей."""

    list_display = ('id', 'subscriber', 'author')
    search_fields = ['subscriber__username', 'author__username']
    list_filter = ['subscriber', 'author']
    raw_id_fields = ['subscriber', 'author']
