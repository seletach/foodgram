from django.contrib import admin
from recipes.models import Ingredient, Recipe, Tag, ShoppingCart, FavoriteRecipe, IngredientsInRecipe


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'get_favorite_count', 'get_tags')
    search_fields = ['name', 'author__username']
    list_filter = ['tags']
    filter_horizontal = ['tags']

    def get_favorite_count(self, obj):
        return FavoriteRecipe.objects.filter(recipe=obj).count()
    get_favorite_count.short_description = 'Количество добавлений в избранное'

    def get_tags(self, obj):
        return '\n'.join(obj.tags.values_list('name', flat=True))
    get_tags.short_description = 'Теги'


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ['name']

admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShoppingCart)
admin.site.register(FavoriteRecipe)
admin.site.register(IngredientsInRecipe)

admin.site.empty_value_display = 'Не задано'