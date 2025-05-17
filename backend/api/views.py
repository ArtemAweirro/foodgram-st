from rest_framework import generics, viewsets, status, views
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse


from .models import (
    Recipe, Ingredient,
    Favorite, ShoppingCart,
    Subscription, User
)
from .serializers import (
    RecipeReadSerializer, RecipeWriteSerializer,
    IngredientSerializer,
    SubscriptionSerializer,
    RecipeInShoppingCartSerializer,
    AvatarUpdateSerializer
)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()

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
            serializer = RecipeReadSerializer(recipe,
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
                return Response({'errors': 'Рецепт уже в корзине'}, status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = RecipeInShoppingCartSerializer(recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            cart_item = ShoppingCart.objects.filter(user=user, recipe=recipe)
            if not cart_item.exists():
                return Response({'errors': 'Рецепта нет в корзине'}, status=status.HTTP_400_BAD_REQUEST)
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        user = request.user
        # Получаем рецепты в корзине пользователя
        recipes = Recipe.objects.filter(in_carts__user=user)

        if not recipes.exists():
            return Response({'errors': 'Корзина покупок пуста'}, status=400)

        # Собираем ингредиенты с суммированием по количеству из всех рецептов в корзине
        ingredients = (recipes
                       .values('ingredients__name', 'ingredients__measurement_unit')
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
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.txt"'

        return response


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class SubscriptionListView(generics.ListAPIView):
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        return Subscription.objects.filter(
            user=self.request.user).select_related('author')


class SubscribeView(views.APIView):
    def post(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)

        if author == user:
            return Response(
                {'errors': 'Нельзя подписаться на себя'},
                status=400
            )
        if Subscription.objects.filter(user=user, author=author).exists():
            return Response({'errors': 'Уже подписаны'}, status=400)

        subscription = Subscription.objects.create(user=user, author=author)
        serializer = SubscriptionSerializer(
            subscription,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)

        subscription = Subscription.objects.filter(user=user, author=author)
        if not subscription.exists():
            return Response(
                {'errors': 'Вы не подписаны'},
                status=status.HTTP_400_BAD_REQUEST)

        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserAvatarView(views.APIView):
    def put(self, request):
        user = request.user
        serializer = AvatarUpdateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.update(user, serializer.validated_data)
            # Отвечаем только полем avatar (URL)
            return Response(
                {'avatar': request.build_absolute_uri(user.avatar.url)})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        user = request.user
        # Удаляем файл аватара, если он есть
        if user.avatar:
            user.avatar.delete(save=False)  # удаляем физически с диска
            user.avatar = None  # обнуляем поле
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
