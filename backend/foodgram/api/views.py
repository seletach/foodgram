from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import render, get_object_or_404

# Create your views here.

from recipes.models import *
from users.models import *
from .serializers import *

# CustomUser

@api_view(['GET', 'POST'])
def user_list(request):
    if request.method == 'POST':
        serializer = CustomUserSerializer(data=request.data,
                                          context={'request': request})
        if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    users = CustomUser.objects.all()
    serializer = CustomUserSerializer(users, many=True,
                                      context={'request': request})
    return Response(serializer.data) 

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
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
def me(request):
    me = request.user
    if me.is_anonymous:
         return Response(False)
    serializer = CustomUserSerializer(me, context={'request': request})
    return Response(serializer.data)

# Tag

@api_view(['GET'])
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
def recipe_list(request):
    if request.method == 'POST':
        serializer = CreateRecipeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    recipes = Recipe.objects.all()
    serializer = RecipeSerializer(recipes, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET', 'PATCH', 'DELETE'])
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

@api_view(['POST', 'DELETE'])
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
def subscription_list(request):
    subscribers = Subscriptions.objects.filter(author=request.user).select_related('subscriber')
    subscriber_users = []
    for subscription in subscribers:
        subscriber_users.append(subscription.subscriber)
    serializer = SubscriptionsSerializer(subscriber_users, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST', 'DELETE'])
def subscribe_detail(request, id):
    pass

# Ingredient

@api_view(['GET'])
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
        serializer = IngredientSerializer(ingredients, many=True)
        return Response(serializer.data)
