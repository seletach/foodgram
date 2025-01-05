from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated,
                                        IsAuthenticatedOrReadOnly,
                                        IsAdminUser)

from django.shortcuts import render, get_object_or_404
from djoser.views import UserViewSet
from django_filters.rest_framework import DjangoFilterBackend

# Create your views here.
from djoser.views import UserViewSet
from recipes.models import *
from users.models import *
from .serializers import *
from .permissions import OwnerOrReadOnly, IsOwnerOnly
from .pagination import CustomPagination
from api.filters import RecipeFilter
from django_filters import rest_framework as filters
from django.http import JsonResponse
import hashlib

import csv
from django.http import HttpResponse

# CustomUser

paginator = CustomPagination()


class CustomUserViewSet(UserViewSet):
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()
    permission_classes = (AllowAny,)
    pagination_class = CustomPagination
    http_method_names = ('get', 'post', 'put', 'patch', 'delete')

@api_view(['PUT', 'DELETE'])
@permission_classes([IsOwnerOnly])
def user_avatar(request):
    user = request.user
    if request.method == 'PUT':
        serializer = AvatarSerializer(user, data=request.data, partial=True, context={'request': request})
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
        try:
            tag = Tag.objects.get(id=id)
            serializer = TagSerializer(tag)
            return Response(serializer.data)
        except Tag.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
    else:
        tags = Tag.objects.all()
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

# Recipe

@api_view(['GET', 'POST'])
@permission_classes([OwnerOrReadOnly])
def recipe_list(request):
    if request.method == 'POST':
        serializer = CreateRecipeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    filterset = RecipeFilter(request.GET, queryset=Recipe.objects.all())
    recipes = filterset.qs
    paginated_recipes = paginator.paginate_queryset(recipes, request)
    serializer = RecipeSerializer(paginated_recipes, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([OwnerOrReadOnly])
def recipe_detail(request, id):
    recipe = Recipe.objects.get(id=id)
    if request.method == 'PATCH':
        serializer = RecipeSerializer(recipe, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = RecipeSerializer(recipe, context={'request': request})
    return Response(serializer.data)

@api_view(['GET']) # ПЕРЕДЕЛАТЬ 
@permission_classes([AllowAny])
def recipe_get_link(request, id):
    recipe = get_object_or_404(Recipe, id=id)
    short_link_suffix = hashlib.md5(str(recipe.id).encode()).hexdigest()[:6]
    short_link = f"https://foodgram.example.org/s/{short_link_suffix}"
    return JsonResponse({"short-link": short_link})

# ShoppingCart

@api_view(['POST', 'DELETE'])
@permission_classes([IsOwnerOnly])
def shoppingcart_detail(request, id):
    recipe = Recipe.objects.get(id=id)
    if request.method == 'POST':
        if ShoppingCart.objects.filter(owner=request.user, recipe=recipe).exists():
            return Response('Рецепт уже находиться в корзине', status=status.HTTP_400_BAD_REQUEST)
        shopping_cart_item = ShoppingCart.objects.create(owner=request.user, recipe=recipe)
        serializer = ShoppingCartSerializer(shopping_cart_item, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    shopping_cart_item = ShoppingCart.objects.get(owner=request.user, recipe=recipe)
    shopping_cart_item.delete()
    return Response('Рецепт удален из корзины', status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsOwnerOnly])
def download_shopping_cart(request):
    if request.method == 'POST':
        shopping_cart_items = ShoppingCart.objects.filter(owner=request.user)
        ingredients_count = {}

        for item in shopping_cart_items:
            recipe = item.recipe
            ingredients_in_recipe = IngredientsInRecipe.objects.filter(recipe=recipe)

            for ingredient_in_recipe in ingredients_in_recipe:
                ingredient_name = ingredient_in_recipe.ingredient.name
                amount = ingredient_in_recipe.amount

                if ingredient_name in ingredients_count:
                    ingredients_count[ingredient_name] += amount
                else:
                    ingredients_count[ingredient_name] = amount

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.csv"'

        writer = csv.writer(response)
        writer.writerow(['Ингредиент', 'Количество', 'Единица измерения'])

        for ingredient_name, amount in ingredients_count.items():
            ingredient = IngredientsInRecipe.objects.filter(ingredient__name=ingredient_name).first()
            measurement_unit = ingredient.ingredient.measurement_unit if ingredient else 'единица'

            writer.writerow([ingredient_name, amount, measurement_unit])

        return response

    return HttpResponse(status=405)



# FavoriteRecipe

@api_view(['POST', 'DELETE'])
@permission_classes([IsOwnerOnly])
def favorite_detail(request, id):
    recipe = Recipe.objects.get(id=id)
    if request.method == 'POST':
        if FavoriteRecipe.objects.filter(user=request.user, recipe=recipe).exists():
            return Response('Рецепт уже находиться в избранном', status=status.HTTP_400_BAD_REQUEST)
        favorite_recipe_item = FavoriteRecipe.objects.create(user=request.user, recipe=recipe)
        serializer = ShoppingCartSerializer(favorite_recipe_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    favorite_recipe_item = FavoriteRecipe.objects.get(user=request.user, recipe=recipe)
    favorite_recipe_item.delete()
    return Response('Рецепт удален из избранного', status=status.HTTP_204_NO_CONTENT)

# Subscriptions

@api_view(['GET'])
@permission_classes([IsOwnerOnly])
def subscription_list(request):
    subscribers = CustomUser.objects.filter(subscriptions__subscriber=request.user)
    paginated_subscribers = paginator.paginate_queryset(subscribers, request)
    serializer = SubscriptionsSerializer(paginated_subscribers,
                                         many=True,
                                         context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def subscribe_detail(request, id):
    author = CustomUser.objects.get(id=id)
    if request.method == 'POST':
        if Subscriptions.objects.filter(author=author, subscriber=request.user).exists():
            return Response(f'Вы уже подписаны на {author.username}', status=status.HTTP_400_BAD_REQUEST)
        # нужна проверка на подписку на самого себя
        Subscriptions.objects.create(author=author, subscriber=request.user)
        serializer = SubscriptionsSerializer(subscriber=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    subscribe = Subscriptions.objects.get(author=author, subscriber=request.user)
    subscribe.delete()
    return Response(f'Вы отписались от {author.username}', status=status.HTTP_204_NO_CONTENT)

# Ingredient

@api_view(['GET'])
@permission_classes([AllowAny])
def ingredient_list_or_detail(request, id=None):
    if id is not None:
        try:
            ingredient = Ingredient.objects.get(id=id)
            serializer = IngredientSerializer(ingredient)
            return Response(serializer.data)
        except Tag.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
    else:
        ingredients = Ingredient.objects.all()
        paginated_ingredients = paginator.paginate_queryset(ingredients, request)
        serializer = IngredientSerializer(paginated_ingredients, many=True)
        return paginator.get_paginated_response(serializer.data)
