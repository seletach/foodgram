import base64
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
from djoser.serializers import TokenCreateSerializer
from recipes.models import *
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from users.models import *


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class CustomUserSerializer(ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    # avatar = Base64ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = ('email',
                  'id',
                  'username',
                  'first_name',
                  'last_name',
                  'is_subscribed',
                  'avatar')

    def get_is_subscribed(self, obj):
        """Метод проверки подписки"""

        request = self.context.get('request')
        user = request.user
        if user.is_anonymous:
            return False
        return Subscriptions.objects.filter(subscriber=user, author=obj.id).exists()


class CustomUserCreateSerializer(ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ('email',
                  'username',
                  'first_name',
                  'last_name',
                  'password')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'username': {'required': True},
            'password': {'write_only': True}
        }

    # def create(self, validated_data):
    #     password = validated_data.pop('password')
    #     user = CustomUser (
    #         email=validated_data['email'],
    #         username=validated_data['username'],
    #         first_name=validated_data['first_name'],
    #         last_name=validated_data['last_name']
    #     )
    #     user.set_password(password)
    #     user.save()
    #     return user
        # return {
        #     'email': user.email,
        #     'id': user.id,
        #     'username': user.username,
        #     'first_name': user.first_name,
        #     'last_name': user.last_name
        # }


class AvatarSerializer(ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = CustomUser
        fields = ('avatar',)


class TagSerializer(ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id',
                  'name',
                  'slug')


class IngredientsInRecipeSerializer(ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientsInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(ModelSerializer):
    tags = TagSerializer(many=True)
    author = CustomUserSerializer()
    ingredients = IngredientsInRecipeSerializer(many=True, source='ingredientsinrecipe_set')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False)

    class Meta:
        model = Recipe
        fields = ('id',
                  'tags',
                  'author',
                  'ingredients',
                  'is_favorited',
                  'is_in_shopping_cart',
                  'name',
                  'image',
                  'text',
                  'cooking_time')
        
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return FavoriteRecipe.objects.filter(user=request.user, recipe=obj).exists()
    
    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(owner=request.user, recipe=obj).exists()


class CreateRecipeSerializer(ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = ('ingredients',
                  'tags',
                  'image',
                  'name',
                  'text',
                  'cooking_time')


class ShoppingCartSerializer(ModelSerializer):
    id = serializers.CharField(source='recipe.id')
    name = serializers.CharField(source='recipe.name')
    cooking_time = serializers.CharField(source='recipe.cooking_time')

    class Meta:
        model = Recipe
        fields = ('id',
                  'name',
                  'cooking_time')


class SubscriptionsSerializer(ModelSerializer):
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('email',
                  'id',
                  'username',
                  'first_name',
                  'last_name',
                  'is_subscribed',
                  'recipes',
                  'recipes_count')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        user = request.user
        if user.is_anonymous:
            return False
        return Subscriptions.objects.filter(subscriber=user, author=obj.id).exists()

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()


class IngredientSerializer(ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id',
                  'name',
                  'measurement_unit')