from datetime import datetime
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import SAFE_METHODS
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from djoser.views import UserViewSet as DjoserUserViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .filters import RecipeFilter
from .models import (
    Recipe, Ingredient, Favorite, Subscription, User, ShoppingCart, ShortLink
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
        instance = get_object_or_404(model, **lookup_fields)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShortLinkRedirectView(View):
    def get(self, request, slug):
        short_link = get_object_or_404(ShortLink, slug=slug)
        return redirect(short_link.original_url)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          OwnerOrReadOnly)
    pagination_class = LimitOffsetPagination
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method not in SAFE_METHODS:
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
            f'Список покупок для пользователя: {user.get_full_name()}',
            f'Дата: {date_str}',
            '',
            'Необходимые ингредиенты:',
            *[
                (f'{idx}. {item["ingredients__name"].capitalize()} '
                 f'— {item["amount"]} {item["ingredients__measurement_unit"]}')
                for idx, item in enumerate(ingredients, start=1)
            ],
            '',
            'Рецепты в корзине:',
            *[
                f'- {recipe.name} (автор: {recipe.author.username})'
                for recipe in recipes
            ]
        ])

        return FileResponse(
            text, as_attachment=True, content_type='text/plain'
        )

    @action(methods=["get"], detail=True, url_path="get-link")
    def get_link(self, request, pk=None):
        if not Recipe.objects.filter(id=pk).exists():
            raise ValidationError(
                {'errors': f'Рецепта с id={pk} не существует'})
        # Получаем путь
        api_path = reverse('recipe-detail', args=[pk])
        # Удаляем префикс "/api", чтобы получить "/recipes/1/"
        frontend_path = api_path.replace('/api', '', 1)
        # Строим абсолютный URL
        full_url = request.build_absolute_uri(frontend_path)
        # Находим или создаем короткую ссылку
        short_link_obj, created = ShortLink.objects.get_or_create(
            original_url=full_url
        )
        return Response(
            data={"short-link":
                  request.build_absolute_uri(f"/s/{short_link_obj.slug}/")}
        )


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
