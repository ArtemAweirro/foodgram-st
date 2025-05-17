from rest_framework import serializers
from djoser.serializers import UserSerializer, UserCreateSerializer, TokenCreateSerializer
from django.core.files.base import ContentFile
from django.contrib.auth import authenticate, get_user_model
from .models import Recipe, RecipeIngredient, Subscription, Ingredient

import base64
import re


User = get_user_model()


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

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


    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, author=obj).exists()
        return False


class CustomUserCreateSerializer(UserCreateSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'password')


class EmailTokenCreateSerializer(TokenCreateSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['email', 'password']

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError(_('Неверный email или пароль'))

            self.user = authenticate(
                request=self.context.get('request'),
                username=user.username,  # `authenticate` по умолчанию ожидает `username`
                password=password,
            )
            if not self.user:
                raise serializers.ValidationError(_('Неверный email или пароль'))
        else:
            raise serializers.ValidationError(_('Необходимо указать email и пароль'))

        return attrs


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = fields


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = Ingredient


class RecipeReadSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_ingredients(self, obj):
        recipe_ingredients = RecipeIngredient.objects.filter(recipe=obj)
        return IngredientInRecipeSerializer(recipe_ingredients, many=True).data

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return obj.favorited_by.filter(user=user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return obj.in_carts.filter(user=user).exists()
        return False


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = IngredientWriteSerializer(many=True)
    image = serializers.ImageField()
    
    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'image', 'name', 'text', 'cooking_time',
        )

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError('Нужно добавить хотя бы один ингредиент.')
        ids = [item['id'] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError('Ингредиенты не должны повторяться.')
        return value

    def create_ingredients(self, ingredients_data, recipe):
        for item in ingredients_data:
            ingredient = Ingredient.objects.get(id=item['id'])
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=item['amount']
            )

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data, author=self.context['request'].user)
        self.create_ingredients(ingredients_data, recipe)
        return recipe


class SubscriptionSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ('author',)


class RecipeInShoppingCartSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class AvatarUpdateSerializer(serializers.Serializer):
    avatar = serializers.CharField()

    def validate_avatar(self, value):
        # ожидаем строку формата data:image/png;base64,.....
        pattern = r'data:image/(?P<ext>.+?);base64,(?P<data>.+)'
        match = re.match(pattern, value)
        if not match:
            raise serializers.ValidationError('Неверный формат изображения.')

        ext = match.group('ext')
        data = match.group('data')

        try:
            decoded_file = base64.b64decode(data)
        except Exception:
            raise serializers.ValidationError('Невозможно декодировать изображение.')

        file_name = f"avatar.{ext}"
        self.validated_data['avatar_file'] = ContentFile(decoded_file, name=file_name)
        return value

    def update(self, instance, validated_data):
        instance.avatar = validated_data['avatar_file']
        instance.save()
        return instance
