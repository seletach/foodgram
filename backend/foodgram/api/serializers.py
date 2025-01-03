from recipes.models import *
from users.models import *
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer


class CustomUserSerializer(ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('email',
                  'id',
                  'username',
                  'first_name',
                  'last_name',
                  'is_subscribed')

    def get_is_subscribed(self, obj):
        """Метод проверки подписки"""

        request = self.context.get('request')
        user = request.user
        if user.is_anonymous:
            return False
        return Subscriptions.objects.filter(subscriber=user, author=obj.id).exists()


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

    class Meta:
        model = Recipe
        fields = ('id',
                  'tags',
                  'author',
                  'ingredients',
                  'is_favorited',
                  'is_in_shopping_cart',
                  'name',
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

    class Meta:
        model = Recipe
        fields = ('ingredients',
                  'tags',
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
    recipes = serializers.SerializerMethodField()

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
    
    def get_recipes_count(self, obj):
        return obj.recipes.count()
    
    def get_is_subscribed(self, obj):
        """Метод проверки подписки"""

        request = self.context.get('request')
        user = request.user
        if user.is_anonymous:
            return False
        return Subscriptions.objects.filter(subscriber=user, author=obj.id).exists()

    def get_recipes(self, obj): # вывести все рецепты подписчиков
        recipes = obj.recipes.all()
        return RecipeSerializer(recipes, many=True).data


class IngredientSerializer(ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id',
                  'name',
                  'measurement_unit')