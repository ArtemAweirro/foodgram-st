from django_filters import rest_framework as filters
from api.models import Recipe


class RecipeFilter(filters.FilterSet):
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart')
    author = filters.NumberFilter(field_name='author__id')
    is_favorited = filters.NumberFilter(method='filter_is_favorited')

    class Meta:
        model = Recipe
        fields = ('author', 'is_in_shopping_cart', 'is_favorited')

    def filter_is_in_shopping_cart(self, recipes_qs, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return recipes_qs.none() if value else recipes_qs
        if value:
            return recipes_qs.filter(in_carts__user=user)
        return recipes_qs.exclude(in_carts__user=user)

    def filter_is_favorited(self, recipes_qs, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return recipes_qs.none() if value else recipes_qs
        if value:
            return recipes_qs.filter(favorites__user=user)
        return recipes_qs.exclude(favorites__user=user)
