from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField

from api.serializers import UserDetailSerializer
from .models import Recipe, RecipeIngredient, Ingredient


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
        source='recipeingredient_set', many=True)
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


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = IngredientWriteSerializer(many=True, write_only=True)
    image = Base64ImageField()
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
                ingredient_id=item['id'],
                amount=item['amount']
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
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
