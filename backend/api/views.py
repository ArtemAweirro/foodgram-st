from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination


from .models import Recipe, Ingredient
from .serializers import RecipeReadSerializer, RecipeWriteSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            return RecipeWriteSerializer
        return RecipeReadSerializer


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()