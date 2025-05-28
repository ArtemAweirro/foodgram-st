from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet

from recipes.views import handle_add_or_remove
from .models import Subscription, User
from .serializers import (
    UserWithSubscriptionsSerializer,
    AvatarUpdateSerializer,
    UserDetailSerializer
)


class UserViewSet(DjoserUserViewSet):
    serializer_class = UserDetailSerializer
    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action == 'me':
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
        return handle_add_or_remove(
            request=request,
            obj=author,
            model=Subscription,
            lookup_fields={'user': user, 'author': author},
            serializer_class=UserWithSubscriptionsSerializer,
            error_messages={'already_exists':
                            f'Вы уже подписаны на {author.get_full_name()}'}
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
