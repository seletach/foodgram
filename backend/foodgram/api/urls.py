from django.urls import include, path
from rest_framework.authtoken import views
from rest_framework.routers import DefaultRouter

from .views import *
from api.authtoken import EmailAuthToken, LogoutView

router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='user')

app_name = 'api'

urlpatterns = [
    # path('api-token-auth/', views.obtain_auth_token),

    # path('auth/token/login/', EmailAuthToken.as_view()), рабочий вариант
    # path('auth/token/logout/', LogoutView.as_view()),
    # path('users/', user_list),
    # path('users/<int:id>/', user_detail),
    # path('users/me/', me),

    path('users/subscriptions/', subscription_list),
    path('users/<int:id>/subscribe/', subscribe_detail),
    path('users/me/avatar/', user_avatar),

    path('tags/', tag_list_or_detail),
    path('tags/<int:id>/', tag_list_or_detail),

    path('recipes/', recipe_list),
    path('recipes/<int:id>/', recipe_detail, name='recipe_detail'),
    path('recipes/<int:id>/get-link/', recipe_get_link),
    path('s/<str:code>/', redirect_to_recipe),

    path('recipes/<int:id>/shopping_cart/', shoppingcart_detail),
    path('recipes/download_shopping_cart/', download_shopping_cart),
    path('recipes/<int:id>/favorite/', favorite_detail),

    path('ingredients/', ingredient_list_or_detail),
    path('ingredients/<int:id>/', ingredient_list_or_detail),

    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls))
]
