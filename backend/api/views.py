import csv
import uuid
import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from djoser.views import UserViewSet
from django.urls import reverse
from django_filters import rest_framework as filters
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
    SubscriptionCreateSerializer,
    ShoppingCartSerializer
)
from recipes.models import (
    Tag,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    FavoriteRecipe,
    ShoppingCart,
)
from users.models import Subscription

paginator = Pagination()

User = get_user_model()

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

    queryset = User.objects.all()
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
        subscribed_authors = User.objects.filter(
            subscriptions__subscriber=user
        ).annotate(
            recipes_count=Count('recipes')
        )

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
        author = get_object_or_404(User, id=id)
        user = request.user

        if request.method == 'POST':
            serializer = SubscriptionCreateSerializer(
                data={'subscriber': user.id, 'author': author.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)

            serializer.save()

            author_with_count = User.objects.filter(id=author.id).annotate(
            recipes_count=Count('recipes')
            ).first()

            serializer = SubscriptionSerializer(
                author_with_count,
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
        """Управление аватаром пользователя через кастомный
        эндпоинт /users/me/avatar/."""
        user = request.user

        if request.method == 'PUT':
            serializer = AvatarSerializer(
                user, data=request.data,
                partial=True,
                context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data,
                                status=status.HTTP_200_OK)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

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

    @staticmethod
    def _add_to_relation(request, user, recipe, relation_model, error_message):
        """Статический метод для добавления в связь (избранное/корзина)."""
        if relation_model.objects.filter(user=user, recipe=recipe).exists():
            return (
                {'detail': error_message},
                status.HTTP_400_BAD_REQUEST
            )

        relation_model.objects.create(user=user, recipe=recipe)
        serializer = UniversalRecipeSerializer(
            recipe,
            context={'request': request}
        )
        return (serializer.data, status.HTTP_201_CREATED)

    @staticmethod
    def _remove_from_relation(user,
                              recipe,
                              relation_model,
                              success_message,
                              error_message):
        """Статический метод для удаления из связи (избранное/корзина)."""
        relation_item = relation_model.objects.filter(
            user=user,
            recipe=recipe
        ).first()

        if not relation_item:
            return (
                {'detail': error_message},
                status.HTTP_400_BAD_REQUEST
            )

        relation_item.delete()
        return (
            {'detail': success_message},
            status.HTTP_204_NO_CONTENT
        )

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
        """Добавление/удаление рецепта в корзину покупок."""
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            data = {'user': user.id, 'recipe': recipe.id}
            serializer = ShoppingCartSerializer(data=data,
                                                context={'request': request})

            if serializer.is_valid():
                serializer.save()
                serializer = UniversalRecipeSerializer(
                    recipe,
                    context={'request': request})
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            else:
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

        elif request.method == 'DELETE':
            result, status_code = self._remove_from_relation(
                user=user,
                recipe=recipe,
                relation_model=ShoppingCart,
                success_message='Рецепт удален из корзины',
                error_message='Рецепт не найден в корзине'
            )
            return Response(result, status=status_code)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачивание списка покупок в формате CSV."""
        shopping_cart_recipes = Recipe.objects.filter(
            recipes_shoppingcart_by_recipe__user=request.user
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
        """Добавление/удаление рецепта в избранное."""
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            result, status_code = self._add_to_relation(
                request=request,
                user=user,
                recipe=recipe,
                relation_model=FavoriteRecipe,
                error_message='Рецепт уже в избранном'
            )
            return Response(result, status=status_code)

        elif request.method == 'DELETE':
            result, status_code = self._remove_from_relation(
                user=user,
                recipe=recipe,
                relation_model=FavoriteRecipe,
                success_message='Рецепт удален из избранного',
                error_message='Рецепт не найден в избранном'
            )
            return Response(result, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
def recipe_get_link(request, id):
    """Генерация короткой ссылки для рецепта."""
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
    """Перенаправление на рецепт по короткой ссылке."""
    recipe = get_object_or_404(Recipe, code=code)
    return redirect('api:recipe_detail', id=recipe.id)
