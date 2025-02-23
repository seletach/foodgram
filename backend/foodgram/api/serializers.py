import base64
import uuid

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from recipes.models import (
    Tag,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    FavoriteRecipe,
    ShoppingCart,
)
from users.models import Subscription, CustomUser

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class CustomUserSerializer(ModelSerializer):
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
        """Метод проверки подписки"""
        request = self.context.get('request')
        user = request.user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(
            subscriber=user, author=obj.id
        ).exists()


class AvatarSerializer(ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = CustomUser
        fields = ('avatar',)

    def validate(self, attrs):
        if 'avatar' not in attrs:
            raise serializers.ValidationError(
                {'detail': 'Поле avatar не может быть пустым'}
            )

        return super().validate(attrs)


class TagSerializer(ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientsInRecipeSerializer(ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient', queryset=Ingredient.objects.all()
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientsInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(ModelSerializer):
    tags = TagSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientsInRecipeSerializer(
        many=True, source='ingredientsinrecipe_set'
    )
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
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return FavoriteRecipe.objects.filter(
            user=request.user, recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe=obj
        ).exists()


class CreateRecipeSerializer(ModelSerializer):
    image = Base64ImageField(allow_null=True)
    ingredients = IngredientsInRecipeSerializer(many=True)

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

    def validate(self, attrs):
        """Валидация для всего объекта"""
        ingredients = attrs.get('ingredients', [])
        if len(ingredients) < 1:
            raise serializers.ValidationError('Минимум 1 ингредиент')

        tags = attrs.get('tags', [])
        if len(tags) < 1:
            raise serializers.ValidationError('Минимум 1 тег')

        return super().validate(attrs)

    def validate_ingredients(self, ingredients):
        """Валидация ингредиентов"""
        ingredient_ids = {ingredient.get('ingredient').id
                          for ingredient in ingredients}

        if len(ingredient_ids) != len(ingredients):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться')

        return ingredients

    def validate_tags(self, tags):
        """Валидация тегов"""
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Такой тег уже добавлен')

        return tags

    def create(self, validated_data):
        """Метод создания рецепта"""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        code = uuid.uuid4().hex[:6]
        recipe = Recipe.objects.create(code=code, **validated_data)
        recipe.tags.set(tags_data)

        ingredients_in_recipe = [
            IngredientsInRecipe(recipe=recipe, **ingredient_data)
            for ingredient_data in ingredients_data
        ]

        IngredientsInRecipe.objects.bulk_create(ingredients_in_recipe)

        return recipe

    def update(self, instance, validated_data):
        """Метод обновления рецепта"""
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        instance = super().update(instance, validated_data)

        if tags_data:
            instance.tags.set(tags_data)

        if ingredients_data:
            instance.ingredientsinrecipe_set.all().delete()
            IngredientsInRecipe.objects.bulk_create(
                [IngredientsInRecipe(recipe=instance, **ingredient_data)
                 for ingredient_data in ingredients_data])

        return instance


class UniversalRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    cooking_time = serializers.IntegerField()
    image = serializers.ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def to_representation(self, instance):
        """Обработка разных моделей"""
        if isinstance(instance, (ShoppingCart, FavoriteRecipe)):
            recipe = instance.recipe
            return {
                'id': recipe.id,
                'name': recipe.name,
                'image': recipe.image.url if recipe.image else None,
                'cooking_time': recipe.cooking_time,
            }
        return super().to_representation(instance)


class SubscriptionSerializer(ModelSerializer):
    recipes_count = serializers.IntegerField(default=0)
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        user = request.user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(
            subscriber=user, author=obj.id
        ).exists()

    def get_recipes(self, obj):
        recipes_limit = self.context.get('recipes_limit', 0)
        recipes = Recipe.objects.filter(author=obj)

        if recipes_limit > 0:
            recipes = recipes[:recipes_limit]

        serializer = UniversalRecipeSerializer(recipes,
                                               many=True,
                                               context=self.context)
        return serializer.data
