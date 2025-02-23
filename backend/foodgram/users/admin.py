from django.contrib import admin

from users.models import CustomUser, Subscriptions


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    """Пользователи."""

    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
    )
    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_filter = ['is_staff']
    ordering = ['username']
    readonly_fields = ['date_joined', 'last_login']


@admin.register(Subscriptions)
class SubscriptionsAdmin(admin.ModelAdmin):
    """Подписки пользователей."""

    list_display = ('id', 'subscriber', 'author')
    search_fields = ['subscriber__username', 'author__username']
    list_filter = ['subscriber', 'author']
    raw_id_fields = ['subscriber', 'author']
