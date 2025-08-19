from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (
    CustomUserViewSet,
    AvatarViewSet,
    TagViewSet,
    RecipeViewSet,
    IngredientViewSet,
    recipe_get_link,
)

router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'recipes', RecipeViewSet, basename='recipe')

app_name = 'api'

urlpatterns = [
    path('recipes/<int:id>/get-link/', recipe_get_link),
    path('users/me/avatar/', AvatarViewSet.as_view(
        {'put': 'update',
         'delete': 'destroy'})),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
]
