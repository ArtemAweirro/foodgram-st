from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse
from djoser.conf import settings
from djoser.views import UserViewSet as DjoserUserViewSet


from .filters import RecipeFilter
from .permissions import OwnerOrReadOnly
from .models import (
    Recipe, Ingredient,
    Favorite, ShoppingCart,
    Subscription, User
)
from .serializers import (
    RecipeReadSerializer, RecipeWriteSerializer, ShortRecipeSerializer,
    IngredientSerializer,
    SubscriptionSerializer,
    RecipeInShoppingCartSerializer,
    AvatarUpdateSerializer,
    CustomUserSerializer, CustomUserCreateSerializer
)


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

        if request.method == 'POST':
            # Проверяем, что рецепт еще не в избранном
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Favorite.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(recipe,
                                               context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            favorite = Favorite.objects.filter(user=user, recipe=recipe)
            if not favorite.exists():
                return Response({'errors': 'Рецепта нет в избранном'},
                                status=status.HTTP_400_BAD_REQUEST)

            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['POST', 'DELETE'])
    def shopping_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в корзине'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = RecipeInShoppingCartSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            cart_item = ShoppingCart.objects.filter(user=user, recipe=recipe)
            if not cart_item.exists():
                return Response(
                    {'errors': 'Рецепта нет в корзине'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['GET'])
    def download_shopping_cart(self, request):
        user = request.user
        # Получаем рецепты в корзине пользователя
        recipes = Recipe.objects.filter(in_carts__user=user)

        if not recipes.exists():
            return Response({'errors': 'Корзина покупок пуста'}, status=400)

        # Собираем ингредиенты с суммированием по количеству из всех рецептов
        ingredients = (recipes
                       .values(
                           'ingredients__name',
                           'ingredients__measurement_unit')
                       .annotate(amount=Sum('recipeingredient__amount'))
                       .order_by('ingredients__name'))

        # Формируем текст для файла
        lines = []
        for item in ingredients:
            name = item['ingredients__name']
            unit = item['ingredients__measurement_unit']
            amount = item['amount']
            lines.append(f"{name} — {amount} {unit}")

        text = "\n".join(lines)

        # Формируем HTTP-ответ с файлом
        response = HttpResponse(text, content_type='text/plain; charset=utf-8')
        response[
            'Content-Disposition'] = 'attachment; filename="shopping_cart.txt"'
        return response

    @action(detail=True, methods=['GET'], url_path='get-link')
    def get_link(self, request, pk=None):
        try:
            self.get_object()
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND)

        # Генерация "короткой" ссылки
        short_id = format(int(pk), 'x')  # hex от id
        short_url = f'https://foodgram.example.org/s/{short_id}'

        return Response({'short-link': short_url})


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend, )
    filterset_fields = ('name',)


class CustomUserViewSet(DjoserUserViewSet):
    serializer_class = CustomUserSerializer
    pagination_class = LimitOffsetPagination

    # Словарь сериализаторов в зависимости от action
    action_serializers = {
        'create': CustomUserCreateSerializer,
        'subscriptions': SubscriptionSerializer,
        'subscribe': SubscriptionSerializer,
        'avatar': AvatarUpdateSerializer,
        'set_password': settings.SERIALIZERS.set_password,
    }

    def get_permissions(self):
        if self.action == 'me':
            return (permissions.IsAuthenticated(),)
        if self.action in ['list', 'retrieve', 'create']:
            return (permissions.AllowAny(),)
        return (permissions.IsAuthenticatedOrReadOnly(),)

    def get_serializer_class(self):
        return self.action_serializers.get(self.action, self.serializer_class)

    @action(detail=False, methods=['GET'])
    def subscriptions(self, request):
        user = request.user
        # Получаем всех пользователей, на которых подписан текущий пользователь
        authors = User.objects.filter(authors__user=user)
        # Извлекаем параметр ?recipes_limit
        recipes_limit = request.query_params.get('recipes_limit')

        page = self.paginate_queryset(authors)
        if page is not None:
            serializer = SubscriptionSerializer(
                page, many=True,
                context={
                    'request': request,
                    'recipes_limit': recipes_limit
                }
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            authors, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['POST', 'DELETE'])
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)
        if author == user:
            return Response(
                {'errors': 'Нельзя подписаться на себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription_qs = Subscription.objects.filter(user=user, author=author)

        if request.method == 'POST':
            if subscription_qs.exists():
                return Response(
                    {'errors': 'Уже подписаны'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(user=user, author=author)

            # Извлекаем параметр ?recipes_limit
            recipes_limit = request.query_params.get('recipes_limit')

            serializer = SubscriptionSerializer(
                author,
                context={
                    'request': request,
                    'recipes_limit': recipes_limit
                }
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not subscription_qs.exists():
                return Response(
                    {'errors': 'Вы не подписаны'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription_qs.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['PUT', 'DELETE'], url_path='me/avatar')
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarUpdateSerializer(data=request.data)
            if serializer.is_valid():
                serializer.update(user, serializer.validated_data)
                avatar_url = request.build_absolute_uri(
                    user.avatar.url) if user.avatar else None
                return Response({'avatar': avatar_url})
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST)
        # DELETE
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
