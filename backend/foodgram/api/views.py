import csv

from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from djoser.views import UserViewSet
from rest_framework import status
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
    UniversalRecipeSerializer,
    SubscriptionsSerializer,
    IngredientSerializer,
)
from recipes.models import (
    Tag,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    FavoriteRecipe,
    ShoppingCart,
    RecipeShortLink,
)
from users.models import Subscriptions, CustomUser

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


@api_view(['PUT', 'DELETE'])
def user_avatar(request):
    """Редактирование или удаление аватара."""
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
    user.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def tag_list_or_detail(request, id=None):
    """Возвращает список или объект тега."""
    if id is not None:
        tag = get_object_or_404(Tag, id=id)
        serializer = TagSerializer(tag)
        return Response(serializer.data)
    else:
        tags = Tag.objects.all()
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)


@api_view(['GET', 'POST'])
def recipe_list(request):
    """Создание или список всех рецептов."""
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
            recipes = recipes.filter(favorited_by__user=request.user)
        if request.GET.get('is_in_shopping_cart') == '1':
            recipes = recipes.filter(added_to_carts__user=request.user)
            # ИЗМЕНИЛ user=owner
    paginated_recipes = paginator.paginate_queryset(recipes, request)
    serializer = RecipeSerializer(
        paginated_recipes, many=True, context={'request': request}
    )
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET', 'PATCH', 'DELETE'])
def recipe_detail(request, id):
    """Получение объекта рецепта или изменение рецепта."""
    recipe = get_object_or_404(Recipe, id=id)
    if request.method in ['PATCH', 'DELETE'] and recipe.author != request.user:
        return Response(
            'Вы не автор этого рецепта', status=status.HTTP_403_FORBIDDEN
        )
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


@api_view(['GET'])
@permission_classes([AllowAny])
def recipe_get_link(request, id):
    """Создание короткой ссылки на рецепт."""
    recipe = get_object_or_404(Recipe, id=id)
    short_link, created = RecipeShortLink.objects.get_or_create(recipe=recipe)
    short_url = request.build_absolute_uri(f'/s/{short_link.code}/')
    return JsonResponse({'short-link': short_url})


def redirect_to_recipe(request, code):
    """Возвращает рецепт по короткой ссылке."""
    short_link = get_object_or_404(RecipeShortLink, code=code)
    return redirect('api:recipe_detail', id=short_link.recipe.id)


@api_view(['POST', 'DELETE'])
def shoppingcart_detail(request, id):
    """Изменение списка покупок."""
    recipe = get_object_or_404(Recipe, id=id)
    if request.method == 'POST':
        if ShoppingCart.objects.filter(
            user=request.user, recipe=recipe  # ИЗМЕНИЛ user=owner
        ).exists():
            return Response(
                'Рецепт уже находиться в корзине',
                status=status.HTTP_400_BAD_REQUEST,
            )
        shopping_cart_item = ShoppingCart.objects.create(
            user=request.user, recipe=recipe  # ИЗМЕНИЛ user=owner
        )
        serializer = UniversalRecipeSerializer(
            shopping_cart_item, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    if not ShoppingCart.objects.filter(
        user=request.user, recipe=recipe  # ИЗМЕНИЛ user=owner
    ).exists():
        return Response(
            'Рецепт не найден в корзине', status=status.HTTP_400_BAD_REQUEST
        )
    shopping_cart_item = get_object_or_404(
        ShoppingCart, user=request.user, recipe=recipe  # ИЗМЕНИЛ user=owner
    )
    shopping_cart_item.delete()
    return Response(
        'Рецепт удален из корзины', status=status.HTTP_204_NO_CONTENT
    )


@api_view(['GET'])
def download_shopping_cart(request):
    """Скачать список покупок."""
    if request.method == 'GET':
        shopping_cart_items = ShoppingCart.objects.filter(user=request.user)
        # ИЗМЕНИЛ user=owner
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


@api_view(['POST', 'DELETE'])
def favorite_detail(request, id):
    """Изменение списка избранных рецептов."""
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
        serializer = UniversalRecipeSerializer(favorite_recipe_item)
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


@api_view(['GET'])
def subscription_list(request):
    """Возвращает список подписчиков пользователя."""
    subscribers = CustomUser.objects.filter(
        subscriptions__subscriber=request.user
    ).annotate(recipes_count=Count('recipes'))
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
    """Изменение списка подписчиков пользователя."""
    author = get_object_or_404(
        CustomUser.objects.annotate(recipes_count=Count('recipes')), id=id
    )
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


@api_view(['GET'])
@permission_classes([AllowAny])
def ingredient_list_or_detail(request, id=None):
    """Возвращает объект или список ингредиентов."""
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
