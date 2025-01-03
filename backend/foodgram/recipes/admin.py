from django.contrib import admin
from recipes.models import Ingredient, Recipe, Tag, ShoppingCart, FavoriteRecipe, IngredientsInRecipe

class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'author',
        'created',
    )
    search_fields = ('title',)
    filter_horizontal = ('ingredients', 'tags')


admin.site.register(Ingredient)
admin.site.register(Tag)
admin.site.register(Recipe)
admin.site.register(ShoppingCart)
admin.site.register(FavoriteRecipe)
admin.site.register(IngredientsInRecipe)

admin.site.empty_value_display = 'Не задано'