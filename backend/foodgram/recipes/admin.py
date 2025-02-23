from django.contrib import admin

from recipes.models import (
    FavoriteRecipe,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    ShoppingCart,
    Tag,
)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Рецепты."""

    list_display = ('name', 'author', 'get_favorite_count', 'get_tags')
    search_fields = ['name', 'author__username']
    list_filter = ['tags']
    filter_horizontal = ['tags']
    exclude = ('code',)

    def get_favorite_count(self, obj):
        return FavoriteRecipe.objects.filter(recipe=obj).count()

    get_favorite_count.short_description = 'Количество добавлений в избранное'

    def get_tags(self, obj):
        return '\n'.join(obj.tags.values_list('name', flat=True))

    get_tags.short_description = 'Теги'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Ингредиенты."""

    list_display = ('name', 'measurement_unit')
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Теги."""

    list_display = ('name', 'slug')
    search_fields = ['name']


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """Список покупок."""

    list_display = ('user', 'recipe')
    raw_id_fields = ('user', 'recipe')


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    """Избранные рецепты."""

    list_display = ('user', 'recipe')
    raw_id_fields = ('user', 'recipe')


@admin.register(IngredientsInRecipe)
class IngredientsInRecipeAdmin(admin.ModelAdmin):
    """Игредиенты в рецептах."""

    list_display = ('recipe', 'ingredient', 'amount')
    raw_id_fields = ('recipe', 'ingredient')


admin.site.empty_value_display = 'Не задано'
