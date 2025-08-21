import csv
import uuid
import logging

from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from djoser.views import UserViewSet
from django.urls import reverse
from rest_framework import status, viewsets
from django_filters import rest_framework as filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response

from api.filters import RecipeFilter, IngredientFilter
from api.pagination import CustomPagination
from api.serializers import (
    AvatarSerializer,
    TagSerializer,
    CreateRecipeSerializer,
    RecipeSerializer,
    UniversalRecipeSerializer,
    SubscriptionSerializer,
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
    pagination_class = CustomPagination

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
        """Подписка/отписка на пользователя.

        Args:
            request: HTTP запрос
            id: ID автора для подписки/отписки

        Returns:
            Response: Результат операции подписки/отписки
        """
        author = get_object_or_404(CustomUser, id=id)
        user = request.user

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'detail': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Subscription.objects.filter(subscriber=user,
                                           author=author).exists():
                return Response(
                    {'detail': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Subscription.objects.create(subscriber=user, author=author)
            serializer = SubscriptionSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(subscriber=user,
                                                       author=author).first()
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


class AvatarViewSet(viewsets.ViewSet):
    """Управление аватаром пользователя.

    Предоставляет endpoints:
    - 'PATCH /api/avatars/<int:pk>/' - обновление аватара.
    - 'DELETE /api/avatars/<int:pk>/' - удаление аватара.

    Permissions:
    - Изменение/удаление: Только владелец аккаунта
    """

    def get_object(self):
        """Получение объекта пользователя.

        Returns:
            CustomUser: Текущий аутентифицированный пользователь
        """
        return self.request.user

    def update(self, request, pk=None):
        """Обновление аватара.

        Args:
            request: HTTP запрос с данными аватара
            pk: ID пользователя (не используется)

        Returns:
            Response: Обновленные данные пользователя или ошибки
        """
        user = self.get_object()
        serializer = AvatarSerializer(
            user, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """Удаление аватара.

        Args:
            request: HTTP запрос
            pk: ID пользователя (не используется)

        Returns:
            Response: Пустой ответ с статусом 204
        """
        user = self.get_object()
        user.avatar.delete()
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_permissions(self):
        """Определение permissions для разных actions."""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
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

    def create(self, request, *args, **kwargs):
        """Создание нового рецепта.

        Returns:
            Response: Созданный рецепт или ошибки валидации
        """
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
                    RecipeSerializer(recipe,
                                     context={'request': request}).data,
                    status=status.HTTP_201_CREATED
                )

        except Exception as error:
            return Response(
                {'detail': str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Обновление существующего рецепта.

        Returns:
            Response: Обновленный рецепт или ошибки доступа/валидации
        """
        instance = self.get_object()
        if instance.author != request.user:
            return Response(
                {'detail':
                 'Вы не автор этого рецепта и не можете его редактировать.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(instance,
                                         data=request.data,
                                         partial=kwargs.get('partial', False))
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
                    RecipeSerializer(instance,
                                     context={'request': request}).data,
                    status=status.HTTP_200_OK
                )

        except Exception as error:
            logger.error(f'Ошибка при обновлении рецепта: {str(error)}')
            return Response(
                {'detail': str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Удаление рецепта.

        Returns:
            Response: Результат удаления или ошибки доступа
        """
        instance = self.get_object()
        if instance.author != request.user:
            return Response(
                {'detail':
                 'Вы не автор этого рецепта и не можете его удалить.'},
                status=status.HTTP_403_FORBIDDEN
            )
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

        elif request.method == 'DELETE':
            shopping_cart_item = ShoppingCart.objects.filter(
                user=user,
                recipe=recipe).first()
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
