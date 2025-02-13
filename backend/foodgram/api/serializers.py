import base64

from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from djoser.serializers import PasswordRetypeSerializer
from django.contrib.auth import authenticate

# from django.utils.translation import gettext_lazy as _
from recipes.models import *
from users.models import *

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
        '''Метод проверки подписки'''

        request = self.context.get('request')
        user = request.user
        if user.is_anonymous:
            return False
        return Subscriptions.objects.filter(
            subscriber=user, author=obj.id
        ).exists()


# class CustomUserCreateSerializer(ModelSerializer):

#     class Meta:
#         model = CustomUser
#         fields = ('email',
#                   'username',
#                   'first_name',
#                   'last_name',
#                   'password')
#         extra_kwargs = {
#             'first_name': {'required': True},
#             'last_name': {'required': True},
#             'username': {'required': True},
#             'password': {'write_only': True}
#         }


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
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientsInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return representation


class RecipeSerializer(ModelSerializer):  # соединить сериалайзеры Recipe
    tags = TagSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientsInRecipeSerializer(
        many=True, source='ingredientsinrecipe_set'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False)

    # request_user = serializers.SerializerMethodField()
    # obj_author = serializers.SerializerMethodField()

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
            #   'request_user',
            #   'obj_author'
        )

    # def get_request_user(self, obj):
    #     request = self.context.get('request')
    #     return request.user.username

    # def get_obj_author(self, obj):
    #     return obj.author.username

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
            owner=request.user, recipe=obj
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

    def validate(self, data):
        ingredients_data = data.get('ingredients', [])
        if len(ingredients_data) < 1:
            raise serializers.ValidationError('Минимум 1 ингредиент')

        tags_data = data.get('tags', [])
        if len(tags_data) < 1:
            raise serializers.ValidationError('Минимум 1 тег')

        ingredient_ids = set()
        tag_ids = set()

        for ingredient in ingredients_data:
            amount = ingredient.get('amount')
            if amount is None or amount < 1:
                raise serializers.ValidationError(
                    'Количество не может быть меньше 1'
                )

            ingredient_instance = ingredient.get('ingredient')
            ingredient_id = ingredient_instance.id
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    f'Ингредиент с ID {ingredient_id} уже добавлен'
                )
            ingredient_ids.add(ingredient_id)

        for tag in tags_data:
            if tag in tag_ids:
                raise serializers.ValidationError(
                    f'Тег с ID {tag} уже добавлен'
                )
            tag_ids.add(tag)

        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        for ingredient_data in ingredients_data:
            IngredientsInRecipe.objects.create(
                recipe=recipe, **ingredient_data
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )
        instance.image = validated_data.get('image', instance.image)
        instance.save()

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.ingredientsinrecipe_set.all().delete()
            for ingredient_data in ingredients_data:
                IngredientsInRecipe.objects.create(
                    recipe=instance, **ingredient_data
                )

        return instance


class ShoppingCartSerializer(ModelSerializer):
    id = serializers.IntegerField(source='recipe.id')
    name = serializers.CharField(source='recipe.name')
    cooking_time = serializers.IntegerField(source='recipe.cooking_time')
    image = serializers.ImageField(source='recipe.image')

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionsSerializer(ModelSerializer):
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField()
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
        return Subscriptions.objects.filter(
            subscriber=user, author=obj.id
        ).exists()

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()

    def get_recipes(self, obj):
        recipes_limit = self.context.get('recipes_limit', 0)
        recipes = Recipe.objects.filter(author=obj)

        if recipes_limit > 0:
            recipes = recipes[:recipes_limit]

        serialized_recipes = []
        for recipe in recipes:
            recipe_data = {
                'id': recipe.id,
                'name': recipe.name,
                'image': recipe.image.url if recipe.image else None,
                'cooking_time': recipe.cooking_time,
            }
            if recipe.image:
                recipe_data['image'] = self.context[
                    'request'
                ].build_absolute_uri(recipe.image.url)
            serialized_recipes.append(recipe_data)
        return serialized_recipes


# class CustomPasswordChangeSerializer(PasswordRetypeSerializer):
#     old_password = serializers.CharField(required=True)
#     new_password = serializers.CharField(required=True)

#     def validate(self, attrs):
#         user = self.context['request'].user
#         old_password = attrs.get('old_password')

#         if not user.check_password(old_password):
#             raise serializers.ValidationError({'old_password': 'Wrong password.'})

#         return super().validate(attrs)
