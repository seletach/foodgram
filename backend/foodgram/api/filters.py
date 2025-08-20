from django_filters import rest_framework as filters

from recipes.models import Recipe, Tag, Ingredient


class RecipeFilter(filters.FilterSet):
    """Фильтр для рецептов с поддержкой множественных фильтров.

    Предоставляет фильтрацию по:
    - Тегам: множественный выбор по slug
    - Автору: по ID автора
    - Избранному: для аутентифицированных пользователей
    - Корзине покупок: для аутентифицированных пользователей
    """

    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    author = filters.NumberFilter(field_name='author__id')
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ['tags', 'author']

    def filter_is_favorited(self, queryset, name, value):
        """Фильтрация рецептов по наличию в избранном.

        Args:
            queryset: Исходный queryset рецептов
            name: Имя поля фильтра
            value: Значение фильтра (True/False)

        Returns:
            QuerySet: Отфильтрованный queryset
        """
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorited_by__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтрация рецептов по наличию в корзине покупок.

        Args:
            queryset: Исходный queryset рецептов
            name: Имя поля фильтра
            value: Значение фильтра (True/False)

        Returns:
            QuerySet: Отфильтрованный queryset
        """
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(added_to_carts__user=user)
        return queryset


class IngredientFilter(filters.FilterSet):
    """Фильтр для ингредиентов по началу названия.

    Предоставляет фильтрацию по:
    - Названию: поиск по началу строки (регистрозависимо)
    """

    name = filters.CharFilter(
        field_name='name',
        lookup_expr='startswith'
    )

    class Meta:
        model = Ingredient
        fields = ['name']
