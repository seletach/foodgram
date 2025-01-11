import uuid
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Tag(models.Model):
    """Модель тега"""

    name = models.CharField(
        verbose_name='Название тега',
        max_length=32,
        help_text='Не более 32 символов',
        unique=True
    )
    slug = models.SlugField(
        verbose_name='Название slug',
        max_length=32,
        help_text='slug должен быть уникальным',
        unique=True
    )

    class Meta:
        verbose_name='Тег'
        verbose_name_plural='Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингредиента"""

    name = models.CharField(
        verbose_name='Название ингредиента',
        max_length=50,
        help_text='Не более 50 символов'
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=50,
        help_text='Не более 50 символов'
    )

    class Meta:
        verbose_name='Ингредиент'
        verbose_name_plural='Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель рецепта"""

    author = models.ForeignKey(
        User,
        verbose_name='Автор рецепта',
        on_delete=models.CASCADE,
        related_name='recipes'
    )
    name = models.CharField(
        verbose_name='Название рецепта',
        max_length=50,
        help_text='Не более 50 символов'
    )
    text = models.TextField(
        verbose_name='Описание рецепта'
    )
    created = models.DateTimeField(
        verbose_name='Дата публикации рецепта',
        auto_now_add=True
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах',
        validators=[MinValueValidator(1)]
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientsInRecipe',
        verbose_name='Ингредиенты',
        help_text='Минимум 2 ингредиента | ',
        validators=[MinValueValidator(1)],
        related_name='recipes',
        # blank=False
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
        help_text='Выберите не менее одного тега | ',
        validators=[MinValueValidator(1)],
        related_name='recipes',
        # blank=False
    )
    image = models.ImageField(
        verbose_name='Картинка',
        upload_to='recipe_images/',
        blank=True
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-created']

    def __str__(self):
        return self.name


class RecipeShortLink(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    code = models.CharField(max_length=10, unique=True, default=uuid.uuid4().hex[:6])


class IngredientsInRecipe(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE,
        validators=[MinValueValidator(2)]
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
    
    def __str__(self):
        return f'{self.ingredient} {self.recipe}'


class ShoppingCart(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Владелец корзины'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
    
    def __str__(self):
        return f'{self.owner} {self.recipe}'


class FavoriteRecipe(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f'{self.user} {self.recipe}'
