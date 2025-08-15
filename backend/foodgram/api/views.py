import csv
import uuid
import logging

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
    TagSerializer,
    CreateRecipeSerializer,
    RecipeSerializer,
    # UniversalRecipeSerializer,
    # SubscriptionSerializer,
    IngredientSerializer,
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

logger = logging.getLogger(__name__)


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


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateRecipeSerializer
        return RecipeSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                recipe = Recipe.objects.create(
                    author=request.user,
                    name=serializer.validated_data['name'],
                    text=serializer.validated_data['text'],
                    cooking_time=serializer.validated_data['cooking_time'],
                    image=serializer.validated_data.get('image')
                )

                recipe.tags.set(serializer.validated_data['tags'])

                ingredients_data = serializer.validated_data['ingredients']
                IngredientsInRecipe.objects.bulk_create([
                    IngredientsInRecipe(
                        recipe=recipe,
                        ingredient=item['id'],
                        amount=item['amount']
                    ) for item in ingredients_data
                ])

                return Response(
                    RecipeSerializer(recipe, context={'request': request}).data,
                    status=status.HTTP_201_CREATED
                )
        
        except Exception as error:
            return Response(
                {'detail': str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        
        try:
            with transaction.atomic():
                for attr, value in serializer.validated_data.items():
                    if attr not in ['ingredients', 'tags']:
                        setattr(instance, attr, value)
                instance.save()
                
                if 'tags' in serializer.validated_data:
                    instance.tags.set(serializer.validated_data['tags'])
                
                if 'ingredients' in serializer.validated_data:
                    instance.ingredients_in_recipe.all().delete()
                    IngredientsInRecipe.objects.bulk_create([
                        IngredientsInRecipe(
                            recipe=instance,
                            ingredient=item['id'],
                            amount=item['amount']
                        ) for item in serializer.validated_data['ingredients']
                    ])

                return Response(
                    RecipeSerializer(instance, context={'request': request}).data,
                    status=status.HTTP_200_OK
                )
    
        except Exception as error:
            logger.error(f'Ошибка при обновлении рецепта: {str(error)}')
            return Response(
                {'detail': str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            with transaction.atomic():
                instance.ingredients_in_recipe.all().delete()
                instance.delete()
                return Response(
                    {'detail': 'Рецепт успешно удалён.'},
                    status=status.HTTP_204_NO_CONTENT
                )
        except Exception as error:
            logger.error(f'Ошибка при удалении рецепта: {str(error)}')
            return Response(
                {'detail': str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )


class FavoriteViewSet(viewsets.ModelViewSet):
    pass