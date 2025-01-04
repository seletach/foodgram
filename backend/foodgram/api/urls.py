from django.urls import path, include
from rest_framework.authtoken import views
from .views import *
from .auth import CustomAuthToken

app_name = 'api'

urlpatterns = [
    path('auth/token/login/', CustomAuthToken.as_view()),

    path('users/', user_list),
    path('users/<int:id>/', user_detail),
    path('users/me/', me),

    path('users/subscriptions/', subscription_list),
    path('users/<int:id>/subscribe/', subscribe_detail),

    path('tags/', tag_list_or_detail),
    path('tags/<int:id>/', tag_list_or_detail),

    path('recipes/', recipe_list),
    path('recipes/<int:id>/', recipe_detail),

    path('recipes/<int:id>/shopping_cart/', shoppingcart_detail),
    path('recipes/<int:id>/favorite/', favorite_detail),

    path('ingredients/', ingredient_list_or_detail),
    path('ingredients/<int:id>/', ingredient_list_or_detail)
]