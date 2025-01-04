from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated,
                                        IsAuthenticatedOrReadOnly,
                                        IsAdminUser)

from django.shortcuts import render, get_object_or_404

# Create your views here.

from recipes.models import *
from users.models import *
from .serializers import *
from .permissions import OwnerOrReadOnly, IsOwnerOnly
from .pagination import CustomPagination

# CustomUser

paginator = CustomPagination()

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def user_list(request):
    if request.method == 'POST':
        serializer = CustomUserSerializer(data=request.data,
                                          context={'request': request})
        if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    users = CustomUser.objects.all()
    paginated_users = paginator.paginate_queryset(users, request)
    serializer = CustomUserSerializer(paginated_users, many=True,
                                      context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([OwnerOrReadOnly])
def user_detail(request, id):
    user = CustomUser.objects.get(id=id)
    if request.method == 'PUT' or request.method == 'PATCH':
        serializer = CustomUserSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = CustomUserSerializer(user, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsOwnerOnly])
def me(request):
    me = request.user
    if me.is_anonymous:
         return Response(False)
    serializer = CustomUserSerializer(me, context={'request': request})
    return Response(serializer.data)

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
    recipes = Recipe.objects.all()
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

# FavoriteRecipe
# Добавлять рецепты в избранное может только залогиненный пользователь.
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

# Subscriptions решить проблемы

@api_view(['GET'])
@permission_classes([IsOwnerOnly])
def subscription_list(request):
    subscribers = CustomUser.objects.filter(subscriptions__subscriber=request.user)
    # paginated_subscribers = paginator.paginate_queryset(subscribers, request)
    serializer = SubscriptionsSerializer(subscribers,
                                         many=True,
                                         context={'request': request})
    return Response(serializer.data)

#     serializer = CustomUserSerializer(paginated_users, many=True,
#                                       context={'request': request})
#     return paginator.get_paginated_response(serializer.data)

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
