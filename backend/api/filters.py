from django_filters import rest_framework as filters
from .models import Recipe


class RecipeFilter(filters.FilterSet):
    is_in_shopping_cart = filters.BooleanFilter(method='filter_is_in_shopping_cart')
    author = filters.NumberFilter(field_name='author__id')

    class Meta:
        model = Recipe
        fields = ('author', 'is_in_shopping_cart')

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none() if value else queryset
        if value:
            return queryset.filter(in_carts__user=user)
        return queryset.exclude(in_carts__user=user)
