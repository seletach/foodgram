from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (
    UserViewSet,
    TagViewSet,
    RecipeViewSet,
    IngredientViewSet,
    recipe_get_link,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'recipes', RecipeViewSet, basename='recipe')

app_name = 'api'

urlpatterns = [
    path('recipes/<int:id>/get-link/', recipe_get_link),
    path('users/me/avatar/', UserViewSet.as_view(
        {'put': 'avatar',
         'delete': 'avatar'})),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
]
