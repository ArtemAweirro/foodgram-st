from rest_framework import serializers
from djoser.serializers import UserSerializer, UserCreateSerializer, TokenCreateSerializer
from django.contrib.auth import authenticate, get_user_model
from .models import Recipe, RecipeIngredient, Subscription


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
        fields = ('email', 'username', 'first_name', 'last_name', 'password')


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


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        read_only=True
    )
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True)
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
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
