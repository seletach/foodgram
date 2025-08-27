import base64
import logging

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from recipes.models import (
    FavoriteRecipe,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    ShoppingCart,
    Tag,
)
from users.models import CustomUser, Subscription

User = get_user_model()

logger = logging.getLogger(__name__)


class Base64ImageField(serializers.ImageField):
    """Кастомное поле для работы с изображениями в base64 формате."""

    def to_internal_value(self, data):
        """Преобразование base64 строки в файл изображения.

        Args:
            data: Данные изображения (base64 строка или файл)

        Returns:
            ContentFile: Файл изображения
        """
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class CustomUserSerializer(ModelSerializer):
    """Сериализатор для модели пользователя с информацией о подписке."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        """Проверка подписки текущего пользователя на автора.

        Args:
            obj: Объект пользователя для проверки

        Returns:
            bool: True если подписка существует, иначе False
        """
        request = self.context.get('request')
        user = request.user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(
            subscriber=user, author=obj.id
        ).exists()


class AvatarSerializer(ModelSerializer):
    """Сериализатор для обновления аватара пользователя."""

    avatar = Base64ImageField()

    class Meta:
        model = CustomUser
        fields = ('avatar',)

    def validate(self, attrs):
        """Валидация данных аватара.

        Args:
            attrs: Атрибуты для валидации

        Returns:
            dict: Валидированные атрибуты

        Raises:
            ValidationError: Если поле avatar отсутствует
        """
        if 'avatar' not in attrs:
            raise serializers.ValidationError(
                {'detail': 'Поле avatar не может быть пустым'}
            )
        return super().validate(attrs)


class TagSerializer(ModelSerializer):
    """Сериализатор для модели тегов."""

    class Meta:
        model = Tag
        fields = ('__all__')


class IngredientSerializer(ModelSerializer):
    """Сериализатор для модели ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('__all__')


class IngredientInRecipeWriteSerializer(ModelSerializer):
    """Сериализатор для записи ингредиентов в рецепте."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientsInRecipe
        fields = ('id', 'amount')

    def validate_amount(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                'Количество должно быть больше 0.'
            )
        return value


class IngredientsInRecipeSerializer(ModelSerializer):
    """Сериализатор для чтения ингредиентов в
    рецепте с дополнительными полями.
    """

    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit')
    id = serializers.ReadOnlyField(source='ingredient.id')

    class Meta:
        model = IngredientsInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(ModelSerializer):
    """Сериализатор для чтения рецептов с дополнительными полями."""

    tags = TagSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientsInRecipeSerializer(many=True,
                                                source='ingredients_in_recipe')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_is_favorited(self, obj):
        """Проверка наличия рецепта в избранном у текущего пользователя.

        Args:
            obj: Объект рецепта

        Returns:
            bool: True если рецепт в избранном, иначе False
        """
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False
        return obj.favorited_by.filter(user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        """Проверка наличия рецепта в корзине покупок у текущего пользователя.

        Args:
            obj: Объект рецепта

        Returns:
            bool: True если рецепт в корзине, иначе False
        """
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False
        return obj.added_to_carts.filter(user=request.user).exists()


class CreateRecipeSerializer(ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    ingredients = IngredientInRecipeWriteSerializer(many=True,
                                                    write_only=True)
    image = Base64ImageField(allow_null=True)
    tags = serializers.PrimaryKeyRelatedField(many=True,
                                              queryset=Tag.objects.all())

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    def to_internal_value(self, data):
        """Преобразование входных данных во внутреннее представление.

        Args:
            data: Входные данные

        Returns:
            dict: Валидированные данные
        """
        return super().to_internal_value(data)

    def validate(self, data):
        """Общая валидация данных рецепта."""

        if 'ingredients' not in data or data['ingredients'] is None:
            raise serializers.ValidationError(
                {'ingredients': 'Обязательное поле!'}
            )

        if 'tags' not in data or data['tags'] is None:
            raise serializers.ValidationError(
                {'tags': 'Обязательное поле!'}
            )

        ingredients = data['ingredients']
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Должен быть хотя бы один ингредиент.'}
            )

        ingredient_ids = [item['id'] for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться.'}
            )

        tags = data['tags']
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Должен быть хотя бы один тег.'}
            )

        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                {'tags': 'Теги не должны повторяться.'}
            )

        return data

    def to_representation(self, instance):
        """Преобразование объекта в сериализованное представление.

        Args:
            instance: Объект рецепта

        Returns:
            dict: Сериализованные данные рецепта
        """
        return RecipeSerializer(instance, context=self.context).data


class UniversalRecipeSerializer(serializers.ModelSerializer):
    """Универсальный сериализатор для краткого представления рецепта."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    cooking_time = serializers.IntegerField()
    image = serializers.ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(CustomUserSerializer):
    """Сериализатор для подписок с информацией о рецептах автора."""

    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
            'recipes',
            'recipes_count'
        )

    def get_recipes(self, obj):
        """Получение списка рецептов автора с ограничением по количеству.

        Args:
            obj: Объект автора

        Returns:
            list: Список рецептов автора
        """
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        queryset = obj.recipes.all()

        if recipes_limit and recipes_limit.isdigit():
            queryset = queryset[:int(recipes_limit)]

        serializer = UniversalRecipeSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return serializer.data

    def get_recipes_count(self, obj):
        """Получение общего количества рецептов автора.

        Args:
            obj: Объект автора

        Returns:
            int: Количество рецептов
        """
        return obj.recipes.count()
