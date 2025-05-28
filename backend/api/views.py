from io import BytesIO
from datetime import datetime
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from django_filters.rest_framework import DjangoFilterBackend
from urlshortner.utils import shorten_url

from .filters import RecipeFilter
from .models import (
    Recipe, Ingredient, Favorite, Subscription, User, ShoppingCart
)
from .serializers import (
    UserWithSubscriptionsSerializer,
    UserDetailSerializer, AvatarUpdateSerializer,
    RecipeReadSerializer, RecipeWriteSerializer, ShortRecipeSerializer,
    IngredientSerializer
)
from .permissions import OwnerOrReadOnly


def handle_add_or_remove(request, obj, model, lookup_fields,
                         serializer_class, error_messages):
    if request.method == 'POST':
        instance, created = model.objects.get_or_create(**lookup_fields)
        if not created:
            raise ValidationError({'errors': error_messages['already_exists']})
        serializer = serializer_class(obj, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    if request.method == 'DELETE':
        exists = model.objects.filter(**lookup_fields).exists()
        if not exists:
            raise ValidationError({'errors': error_messages['does_not_exist']})
        instance = model.objects.get(**lookup_fields)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (OwnerOrReadOnly,)
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
            error_messages={
                'already_exists': f'Рецепт "{recipe.name}" уже в избранном',
                'does_not_exist': f'Рецепта "{recipe.name}" нет в избранном'
            }
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
            error_messages={
                'already_exists': f'Рецепт "{recipe.name}" уже в корзине',
                'does_not_exist': f'Рецепта "{recipe.name}" нет в корзине'
            }
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
                       .annotate(amount=Sum('recipe_ingredients__amount'))
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


class UserViewSet(DjoserUserViewSet):
    serializer_class = UserDetailSerializer
    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action in ('me', 'avatar', 'subscribe'):
            return (permissions.IsAuthenticated(),)
        return super().get_permissions()

    @action(detail=False, methods=['GET'])
    def subscriptions(self, request):
        user = request.user
        # Получаем всех пользователей, на которых подписан текущий пользователь
        authors = User.objects.filter(authors__user=user)
        # Извлекаем параметр ?recipes_limit
        recipes_limit = request.query_params.get('recipes_limit')
        page = self.paginate_queryset(authors)
        serializer = UserWithSubscriptionsSerializer(
            page, many=True,
            context={
                'request': request,
                'recipes_limit': recipes_limit
            }
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['POST', 'DELETE'])
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)
        if request.method == 'POST' and author == user:
            raise ValidationError({'errors': 'Нельзя подписаться на себя'})
        return handle_add_or_remove(
            request=request,
            obj=author,
            model=Subscription,
            lookup_fields={'user': user, 'author': author},
            serializer_class=UserWithSubscriptionsSerializer,
            error_messages={
                'already_exists':
                    f'Вы уже подписаны на {author.get_full_name()}',
                'does_not_exist':
                    f'Вы не подписаны на {author.get_full_name()}'
            }
        )

    @action(detail=False, methods=['PUT', 'DELETE'], url_path='me/avatar')
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarUpdateSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.update(user, serializer.validated_data)
                avatar_url = request.build_absolute_uri(
                    user.avatar.url) if user.avatar else None
                return Response({'avatar': avatar_url})
        # DELETE
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
