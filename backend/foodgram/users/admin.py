from django.contrib import admin
from users.models import CustomUser, Subscription


class CustomUserAdmin(admin.ModelAdmin):
    search_fields = ['username', 'email']


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Subscription)
