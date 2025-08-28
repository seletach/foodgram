import csv
import uuid
import logging

from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from djoser.views import UserViewSet
from django.urls import reverse
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response

from api.filters import RecipeFilter, IngredientFilter
from api.pagination import Pagination
from api.permissions import IsRecipeAuthor
from api.serializers import (
    AvatarSerializer,
    TagSerializer,
    CreateRecipeSerializer,
    RecipeSerializer,
    UniversalRecipeSerializer,
    SubscriptionSerializer,
    IngredientSerializer,
    SubscriptionCreateSerializer
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

paginator = Pagination()

logger = logging.getLogger(__name__)


class UserViewSet(UserViewSet):
    """CRUD для пользователей, наследуется от Djoser UserViewSet.

    Предоставляет endpoints:
    - 'GET /api/users/' - список всех пользователей.
    - 'POST /api/users/' - регистрация нового пользователя.
    - 'GET /api/users/<int:id>/' - информация о пользователе.
    - 'GET /api/users/me/' - информация о текущем пользователе.
    - 'POST/DELETE /api/users/<int:id>/subscribe/'
                                        - подписка/отписка на пользователя.
    - 'GET /api/users/subscriptions/' - список подписок текущего пользователя.

    Дополнительные actions:
    - 'POST /api/users/set_password/' - смена пароля.
    - 'POST /api/users/reset_password/' - сброс пароля.
    - 'POST /api/users/reset_password_confirm/' - подтверждение сброса пароля.

    Permissions:
    - Регистрация: AllowAny
    - Просмотр профиля: AllowAny
    - Изменение данных: Только владелец аккаунта
    - Подписки: Только аутентифицированные пользователи
    """

    queryset = CustomUser.objects.all()
    pagination_class = Pagination

    def get_permissions(self):
        """Определение permissions для разных actions.

        Returns:
            list: Список permission классов для action 'me'
        """
        if self.action == 'me':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        """Получение списка подписок пользователя.

        Returns:
            Response: Пагинированный список авторов с количеством рецептов
        """
        user = request.user
        subscribed_authors = CustomUser.objects.filter(
            subscriptions__subscriber=user
        ).annotate(recipes_count=Count('recipes'))

        paginated_authors = paginator.paginate_queryset(subscribed_authors,
                                                        request)
        serializer = SubscriptionSerializer(
            paginated_authors,
            many=True,
            context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        """Подписка/отписка на пользователя."""
        author = get_object_or_404(CustomUser, id=id)
        user = request.user

        if request.method == 'POST':
            serializer = SubscriptionCreateSerializer(
                data={'subscriber': user.id, 'author': author.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)

            serializer.save()

            serializer = SubscriptionSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        subscription = Subscription.objects.filter(subscriber=user,
                                                   author=author)
        if not subscription:
            return Response(
                {'detail': 'Вы не подписаны на этого пользователя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.delete()
        return Response(
            {'detail': 'Вы успешно отписались'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['put', 'delete'],
            permission_classes=[IsAuthenticated], url_path='me/avatar')
    def avatar(self, request):
        """Управление аватаром пользователя через кастомный эндпоинт /users/me/avatar/."""
        user = request.user

        if request.method == 'PUT':
            serializer = AvatarSerializer(
                user, data=request.data, partial=True, context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
                user.save()
                return Response(
                    {'detail': 'Аватар успешно удален'},
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    {'detail': 'Аватар не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )
        return Response(
            {'detail': 'Метод не разрешен'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Информация о тегах, только чтение.

    Предоставляет endpoints:
    - 'GET /api/tags/' - список всех тегов.
    - 'GET /api/tags/<int:id>/' - информация о теге.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Информация об ингредиентах, только чтение.

    Предоставляет endpoints:
    - 'GET /api/ingredients/' - список всех ингредиентов.
    - 'GET /api/ingredients/<int:id>/' - информация об ингредиенте.

    Фильтрация:
    - По началу названия, регистрозависимо: '?name=<str:name>'
    """

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """CRUD для рецетов.

    Предоставляет endpoints:
    - 'GET /api/recipes/' - список всех рецептов.
    - 'POST /api/recipes/' - создание рецепта.
    - 'GET /api/recipes/<int:id>/' - информация о рецепте.
    - 'PATCH /api/recipes/<int:id>/' - редактирование рецепта.
    - 'DELETE /api/recipes/<int:id>/' - удаление рецепта.

    Дополнительные actions:
    - 'POST/DELETE /api/recipes/<int:id>/favorite/'
                                        - добавление рецепта в избранное.
    - 'POST/DELETE /api/recipes/<int:id>/shopping_cart/'
                                        - добавление рецепта в корзину.
    - 'GET /api/recipes/download_shopping_cart/' - скачивание рецепта.

    Фильтрация:
    - По тегам: '?tags=<slug:name_1>, <slug:name_2>'
    - По author_id: '?author=<int:id>'
    - По избранным: '?is_favorited=True/False'
    - По наличию в корзине: '?is_in_shopping_cart=True/False'

    Permissions:
    - Создание: Только аутентифицированные пользователи
    - Изменение/удаление: Только автор рецепта
    - Фильтры is_favorited, is_in_shopping_cart: Только для аутентифицированных
    """

    queryset = Recipe.objects.all()
    pagination_class = Pagination
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_permissions(self):
        """Определение permissions для разных actions."""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsRecipeAuthor()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """Выбор serializer класса в зависимости от action.

        Returns:
            Serializer: CreateRecipeSerializer для create/update,
                       RecipeSerializer для остальных случаев
        """
        if self.action in ['create', 'update', 'partial_update']:
            return CreateRecipeSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        """Создание рецепта с автором из контекста запроса."""
        serializer.save(author=self.request.user)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление рецепта в корзину покупок.

        Args:
            request: HTTP запрос
            pk: ID рецепта

        Returns:
            Response: Результат операции с корзиной
        """
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже находится в корзине'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = UniversalRecipeSerializer(
                recipe,
                context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        shopping_cart_item = ShoppingCart.objects.filter(user=user,
                                                         recipe=recipe)
        if not shopping_cart_item:
            return Response(
                {'detail': 'Рецепт не найден в корзине'},
                status=status.HTTP_400_BAD_REQUEST
            )
        shopping_cart_item.delete()
        return Response(
            {'detail': 'Рецепт удален из корзины'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачивание списка покупок в формате CSV.

        Returns:
            HttpResponse: CSV файл со списком ингредиентов
        """
        shopping_cart_recipes = Recipe.objects.filter(
            added_to_carts__user=request.user
        )

        ingredients = IngredientsInRecipe.objects.filter(
            recipe__in=shopping_cart_recipes
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount'))

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = ('attachment;'
                                           'filename="shopping_cart.csv"')

        writer = csv.writer(response)
        writer.writerow(['Ингредиент', 'Количество', 'Единица измерения'])

        for item in ingredients:
            writer.writerow([
                item['ingredient__name'],
                item['total_amount'],
                item['ingredient__measurement_unit']
            ])

        return response

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта в избранное.

        Args:
            request: HTTP запрос
            pk: ID рецепта

        Returns:
            Response: Результат операции с избранным
        """
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if FavoriteRecipe.objects.filter(user=user,
                                             recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            FavoriteRecipe.objects.create(user=user, recipe=recipe)
            serializer = UniversalRecipeSerializer(
                recipe,
                context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            favorite_item = FavoriteRecipe.objects.filter(
                user=user,
                recipe=recipe).first()
            if not favorite_item:
                return Response(
                    {'detail': 'Рецепт не найден в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorite_item.delete()
            return Response(
                {'detail': 'Рецепт удален из избранного'},
                status=status.HTTP_204_NO_CONTENT
            )


@api_view(['GET'])
@permission_classes([AllowAny])
def recipe_get_link(request, id):
    """Генерация короткой ссылки для рецепта.

    Args:
        request: HTTP запрос
        id: ID рецепта

    Returns:
        JsonResponse: Короткая ссылка на рецепт
    """
    recipe = get_object_or_404(Recipe, id=id)

    if not recipe.code:
        with transaction.atomic():
            code = uuid.uuid4().hex[:6]
            try:
                recipe.code = code
                recipe.save()
            except IntegrityError:
                code = uuid.uuid4().hex[:6]
                recipe.code = code
                recipe.save()

    short_url = request.build_absolute_uri(
        reverse('recipe_short', kwargs={'code': recipe.code}))
    return JsonResponse({'short-link': short_url})


def redirect_to_recipe(request, code):
    """Перенаправление на рецепт по короткой ссылке.

    Args:
        request: HTTP запрос
        code: Код короткой ссылки

    Returns:
        HttpResponseRedirect: Перенаправление на полный рецепт
    """
    recipe = get_object_or_404(Recipe, code=code)
    return redirect('api:recipe_detail', id=recipe.id)
