from rest_framework import serializers
from djoser.serializers import UserSerializer
from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField
from .models import Recipe, Ingredient, RecipeIngredient, Subscription


User = get_user_model()


class UserDetailSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField(required=True)
    avatar = serializers.ImageField(required=True, allow_null=True)

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
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'recipes', 'recipes_count', 'avatar', 'is_subscribed'
        )
        read_only_fields = fields

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated
            and Subscription.objects.filter(author=obj).exists()
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit') if request else None
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


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeReadSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = fields


class IngredientWriteSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserDetailSerializer(read_only=True)
    ingredients = IngredientInRecipeReadSerializer(
        source='recipe_ingredients', many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = fields

    def get_is_favorited(self, recipe_obj):
        user = self.context.get('request').user
        return (user.is_authenticated
                and recipe_obj.favorites.filter(user=user).exists())

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return obj.in_carts.filter(user=user).exists()
        return False


class ShortRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class StrictBase64ImageField(Base64ImageField):
    def to_internal_value(self, data):
        if data == "":
            raise serializers.ValidationError(
                'Поле image не может быть пустой строкой.')
        return super().to_internal_value(data)


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = IngredientWriteSerializer(many=True, write_only=True)
    image = StrictBase64ImageField(required=True, allow_null=False)
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'image', 'name', 'text', 'cooking_time',
        )

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                'Нужно добавить хотя бы один ингредиент.')
        ids = [item['id'] for item in ingredients]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.')
        return ingredients

    def validate(self, attrs):
        ingredients = attrs.get('ingredients')
        self.validate_ingredients(ingredients)
        return attrs

    def create_ingredients(self, ingredients_data, recipe):
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        validated_data['author'] = self.context['request'].user
        recipe = super().create(validated_data)
        self.create_ingredients(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        # Извлекаем ингредиенты, если они есть в запросе
        ingredients_data = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        # Очистить старые ингредиенты
        instance.ingredients.clear()
        # Создать новые связи
        self.create_ingredients(ingredients_data, instance)
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data
