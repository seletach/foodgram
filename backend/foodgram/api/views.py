import csv
import uuid

from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from djoser.views import UserViewSet
from django.urls import reverse
from rest_framework import status,viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.pagination import CustomPagination
from api.serializers import (
    AvatarSerializer,
    # TagSerializer,
    # CreateRecipeSerializer,
    # RecipeSerializer,
    # UniversalRecipeSerializer,
    # SubscriptionSerializer,
    # IngredientSerializer,
)
from recipes.models import (
    Tag,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    FavoriteRecipe,
    ShoppingCart,
)
from users.models import Subscription, CustomUser

paginator = CustomPagination()


class CustomUserViewSet(UserViewSet):
    """Вьюсет для объекта пользователя:
    Регистрация токенов, POST, GET, PATCH, DELETE."""
    queryset = CustomUser.objects.all()
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        return super().get_permissions()


class AvatarViewSet(viewsets.ViewSet):
    """
    ViewSet для редактирования или удаления аватара пользователя.
    """

    def get_object(self):
        return self.request.user

    def update(self, request, pk=None):
        """Обновление аватара."""
        user = self.get_object()
        serializer = AvatarSerializer(
            user, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """Удаление аватара."""
        user = self.get_object()
        user.avatar.delete()
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
