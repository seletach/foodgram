import csv
import hashlib
import re

from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import (
    UserCreateSerializer,
    UserSerializer,
    SetPasswordSerializer,
)
from djoser.permissions import *
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import RecipeFilter
from api.pagination import CustomPagination
from api.permissions import (
    DenyAllPermission,
    IsOwnerOnly,
    OwnerOrReadOnly,
    OwnerOrAdminOrReadOnly,
)
from api.serializers import *
from recipes.models import *
from users.models import *

paginator = CustomPagination()

# CustomUser


class CustomUserViewSet(UserViewSet):
    queryset = CustomUser.objects.all()
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'set_password':
            return SetPasswordSerializer
        return CustomUserSerializer

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        return super().get_permissions()


@api_view(['PUT', 'DELETE'])
def user_avatar(request):
    user = request.user
    if request.method == 'PUT':
        serializer = AvatarSerializer(
            user, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    user.avatar.delete()
    user.avatar = None
    user.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


# Tag


@api_view(['GET'])
@permission_classes([AllowAny])
def tag_list_or_detail(request, id=None):
    if id is not None:
        tag = get_object_or_404(Tag, id=id)
        serializer = TagSerializer(tag)
        return Response(serializer.data)
    else:
        tags = Tag.objects.all()
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)


# Recipe


@api_view(['GET', 'POST'])
def recipe_list(request):
    if request.method == 'POST':
        serializer = CreateRecipeSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            recipe = serializer.save(author=request.user)
            return Response(
                RecipeSerializer(recipe, context={'request': request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    queryset = Recipe.objects.all()
    filterset = RecipeFilter(request.GET, queryset)
    recipes = filterset.qs
    if request.user.is_authenticated:
        if request.GET.get('is_favorited') == '1':
            recipes = recipes.filter(favoriterecipe__user=request.user)
        if request.GET.get('is_in_shopping_cart') == '1':
            recipes = recipes.filter(shoppingcart__owner=request.user)
    paginated_recipes = paginator.paginate_queryset(recipes, request)
    serializer = RecipeSerializer(
        paginated_recipes, many=True, context={'request': request}
    )
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes(
    [OwnerOrAdminOrReadOnly]
)  # не работает, аноним может только читать, но не автор может редактировать
def recipe_detail(request, id):
    recipe = get_object_or_404(Recipe, id=id)
    if request.method == 'PATCH':
        serializer = CreateRecipeSerializer(
            recipe,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                RecipeSerializer(recipe, context={'request': request}).data,
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        recipe.delete()
        return Response('Рецепт удален', status=status.HTTP_204_NO_CONTENT)
    serializer = RecipeSerializer(recipe, context={'request': request})
    return Response(serializer.data)


# RecipeShortLink


@api_view(['GET'])
@permission_classes([AllowAny])
def recipe_get_link(request, id):
    recipe = get_object_or_404(Recipe, id=id)
    short_link, created = RecipeShortLink.objects.get_or_create(recipe=recipe)
    short_url = f'{settings.SITE_URL}/s/{short_link.code}/'
    return JsonResponse({'short-link': short_url})


def redirect_to_recipe(request, code):
    short_link = get_object_or_404(RecipeShortLink, code=code)
    return redirect('api:recipe_detail', id=short_link.recipe.id)


# ShoppingCart


@api_view(['POST', 'DELETE'])
def shoppingcart_detail(request, id):
    recipe = get_object_or_404(Recipe, id=id)
    if request.method == 'POST':
        if ShoppingCart.objects.filter(
            owner=request.user, recipe=recipe
        ).exists():
            return Response(
                'Рецепт уже находиться в корзине',
                status=status.HTTP_400_BAD_REQUEST,
            )
        shopping_cart_item = ShoppingCart.objects.create(
            owner=request.user, recipe=recipe
        )
        serializer = ShoppingCartSerializer(
            shopping_cart_item, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    if not ShoppingCart.objects.filter(
        owner=request.user, recipe=recipe
    ).exists():
        return Response(
            'Рецепт не найден в корзине', status=status.HTTP_400_BAD_REQUEST
        )
    shopping_cart_item = get_object_or_404(
        ShoppingCart, owner=request.user, recipe=recipe
    )
    shopping_cart_item.delete()
    return Response(
        'Рецепт удален из корзины', status=status.HTTP_204_NO_CONTENT
    )


@api_view(['GET'])
def download_shopping_cart(request):
    if request.method == 'GET':
        shopping_cart_items = ShoppingCart.objects.filter(owner=request.user)
        ingredients_count = {}
        for item in shopping_cart_items:
            recipe = item.recipe
            ingredients_in_recipe = IngredientsInRecipe.objects.filter(
                recipe=recipe
            )
            for ingredient_in_recipe in ingredients_in_recipe:
                ingredient_name = ingredient_in_recipe.ingredient.name
                amount = ingredient_in_recipe.amount
                if ingredient_name in ingredients_count:
                    ingredients_count[ingredient_name] += amount
                else:
                    ingredients_count[ingredient_name] = amount
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename=shopping_cart.csv'
        )
        writer = csv.writer(response)
        writer.writerow(['Ингредиент', 'Количество', 'Единица измерения'])
        for ingredient_name, amount in ingredients_count.items():
            ingredient = IngredientsInRecipe.objects.filter(
                ingredient__name=ingredient_name
            ).first()
            measurement_unit = (
                ingredient.ingredient.measurement_unit
                if ingredient
                else 'единица'
            )
            writer.writerow([ingredient_name, amount, measurement_unit])
        return response
    return HttpResponse(status=405)


# FavoriteRecipe


@api_view(['POST', 'DELETE'])
def favorite_detail(request, id):
    recipe = get_object_or_404(Recipe, id=id)
    if request.method == 'POST':
        if FavoriteRecipe.objects.filter(
            user=request.user, recipe=recipe
        ).exists():
            return Response(
                'Рецепт уже находиться в избранном',
                status=status.HTTP_400_BAD_REQUEST,
            )
        favorite_recipe_item = FavoriteRecipe.objects.create(
            user=request.user, recipe=recipe
        )
        serializer = ShoppingCartSerializer(favorite_recipe_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    if not FavoriteRecipe.objects.filter(
        user=request.user, recipe=recipe
    ).exists():
        return Response(
            'Рецепт не найден в избранном', status=status.HTTP_400_BAD_REQUEST
        )
    favorite_recipe_item = get_object_or_404(
        FavoriteRecipe, user=request.user, recipe=recipe
    )
    favorite_recipe_item.delete()
    return Response(
        'Рецепт удален из избранного', status=status.HTTP_204_NO_CONTENT
    )


# Subscriptions


@api_view(['GET'])
def subscription_list(request):
    subscribers = CustomUser.objects.filter(
        subscriptions__subscriber=request.user
    )
    paginated_subscribers = paginator.paginate_queryset(subscribers, request)
    recipes_limit = int(request.query_params.get('recipes_limit', 0))
    serializer = SubscriptionsSerializer(
        paginated_subscribers,
        many=True,
        context={'request': request, 'recipes_limit': recipes_limit},
    )
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST', 'DELETE'])
def subscribe_detail(request, id):
    author = get_object_or_404(CustomUser, id=id)
    recipes_limit = int(request.query_params.get('recipes_limit', 0))
    if request.method == 'POST':
        if request.user == author:
            return Response(
                'Вы не можете подписаться на самого себя',
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Subscriptions.objects.filter(
            author=author, subscriber=request.user
        ).exists():
            return Response(
                f'Вы уже подписаны на {author.username}',
                status=status.HTTP_400_BAD_REQUEST,
            )
        subscription = Subscriptions.objects.create(
            author=author, subscriber=request.user
        )
        serializer = SubscriptionsSerializer(
            subscription.author,
            context={'request': request, 'recipes_limit': recipes_limit},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    if not Subscriptions.objects.filter(
        author=author, subscriber=request.user
    ).exists():
        return Response(
            'Подписка не найдена', status=status.HTTP_400_BAD_REQUEST
        )
    subscribe = get_object_or_404(
        Subscriptions, author=author, subscriber=request.user
    )
    subscribe.delete()
    return Response(
        f'Вы отписались от {author.username}',
        status=status.HTTP_204_NO_CONTENT,
    )


# Ingredient


@api_view(['GET'])
@permission_classes([AllowAny])
def ingredient_list_or_detail(request, id=None):
    if id is not None:
        ingredient = get_object_or_404(Ingredient, id=id)
        serializer = IngredientSerializer(ingredient)
        return Response(serializer.data)
    else:
        name = request.query_params.get('name', None)
        if name:
            ingredients = Ingredient.objects.filter(name__icontains=name)
        else:
            ingredients = Ingredient.objects.all()
        serializer = IngredientSerializer(ingredients, many=True)
        return Response(serializer.data)
