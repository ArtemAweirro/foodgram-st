from rest_framework import viewsets, status, permissions
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from io import BytesIO
from datetime import datetime
from urlshortner.utils import shorten_url

from api.models import ShoppingCart, Favorite
from .permissions import OwnerOrReadOnly
from .models import Recipe, Ingredient
from .filters import RecipeFilter
from .serializers import (
    RecipeReadSerializer, RecipeWriteSerializer, ShortRecipeSerializer,
    IngredientSerializer
)


@staticmethod
def handle_add_or_remove(request, obj, model, lookup_fields,
                         serializer_class, error_messages):
    if request.method == 'POST':
        instance, created = model.objects.get_or_create(**lookup_fields)
        if not created:
            raise ValidationError({'errors': error_messages['already_exists']})
        serializer = serializer_class(obj, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    if request.method == 'DELETE':
        instance = get_object_or_404(model, **lookup_fields)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly, OwnerOrReadOnly)
    pagination_class = LimitOffsetPagination
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            return RecipeWriteSerializer
        return RecipeReadSerializer

    @action(detail=True, methods=['POST', 'DELETE'])
    def favorite(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        return handle_add_or_remove(
            request=request,
            obj=recipe,
            model=Favorite,
            lookup_fields={'user': user, 'recipe': recipe},
            serializer_class=ShortRecipeSerializer,
            error_messages={'already_exists':
                            f'Рецепт "{recipe.name}" уже в избранном'}
        )

    @action(detail=True, methods=['POST', 'DELETE'])
    def shopping_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        return handle_add_or_remove(
            request=request,
            obj=recipe,
            model=ShoppingCart,
            lookup_fields={'user': user, 'recipe': recipe},
            serializer_class=ShortRecipeSerializer,
            error_messages={'already_exists':
                            f'Рецепт "{recipe.name}" уже в корзине'}
        )

    @action(detail=False, methods=['GET'])
    def download_shopping_cart(self, request):
        user = request.user
        # Получаем рецепты в корзине пользователя
        recipes = Recipe.objects.filter(in_carts__user=user)

        # Собираем ингредиенты с суммированием по количеству из всех рецептов
        ingredients = (recipes
                       .values(
                           'ingredients__name',
                           'ingredients__measurement_unit')
                       .annotate(amount=Sum('recipeingredient__amount'))
                       .order_by('ingredients__name'))

        # Формируем текст для файла
        date_str = datetime.now().strftime('%d.%m.%Y')
        text = '\n'.join([
            ('Список покупок для пользователя: '
             f'{user.get_full_name()}'),
            f'Дата: {date_str}',
            '',
            'Необходимые ингредиенты:',
            *[
                f'{idx + 1}. {item["ingredients__name"].capitalize()} — '
                f'{item["amount"]} {item["ingredients__measurement_unit"]}'
                for idx, item in enumerate(ingredients)
            ],
            '',
            'Рецепты в корзине:',
            *[
                f'- {recipe.name} (автор: {recipe.author.get_full_name()})'
                for recipe in recipes
            ]
        ])
        buffer = BytesIO()
        buffer.write(text.encode('utf-8'))
        buffer.seek(0)
        return FileResponse(
            buffer, as_attachment=True, content_type='text/plain'
        )

    @action(methods=["get"], detail=True, url_path="get-link")
    def get_link(self, request, pk=None):
        get_object_or_404(Recipe, id=pk)
        default_link = request.build_absolute_uri(f"/api/recipes/{pk}/")
        short_link = shorten_url(url=default_link, is_permanent=False)
        return Response(data={"short-link": short_link})


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend, )
    filterset_fields = ('name',)
