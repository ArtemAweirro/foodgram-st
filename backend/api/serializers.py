from rest_framework import serializers
from djoser.serializers import UserSerializer
from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField

from recipes.serializers import ShortRecipeSerializer
from .models import Subscription


User = get_user_model()


class UserDetailSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )
        read_only_fields = fields

    def get_is_subscribed(self, user_obj):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Subscription.objects.filter(
                user=request.user, author=user_obj).exists()
        )


class UserWithSubscriptionsSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes.count')

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'recipes', 'recipes_count', 'avatar'
        )
        read_only_fields = fields

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = self.context.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit and limit.isdigit():
            recipes = recipes[:int(limit)]

        return ShortRecipeSerializer(
            recipes, many=True,
            context={'request': request}
        ).data


class AvatarUpdateSerializer(serializers.Serializer):
    avatar = Base64ImageField()

    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance
