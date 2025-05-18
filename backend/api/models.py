from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


username_validator = RegexValidator(
    regex=r'^[\w.@+-]+$',
    message='Имя пользователя может содержать только буквы, цифры и символы . @ + - _ и должно заканчиваться на Z.'
)


class User(AbstractUser):
    email = models.EmailField(unique=True, max_length=254)
    username = models.CharField(
        unique=True, max_length=150,
        validators=(username_validator,))
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    avatar = models.ImageField(
        upload_to='users/images/',
        null=True,
        blank=True,
        verbose_name='Аватар'
    )

    class Meta:
        ordering = ('id',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(User, related_name='follower', on_delete=models.CASCADE)
    author = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)

    class Meta:
        ordering = ('author',)
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'


class Ingredient(models.Model):
    name = models.CharField(verbose_name='Название', max_length=100)
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=50
    )

    class Meta:
        ordering = ('id',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def _str_(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               related_name='recipes')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты'
    )
    name = models.CharField(verbose_name='Название', max_length=255)
    text = models.TextField(verbose_name='Описание')
    image = models.ImageField(
        upload_to='recipe/images/',
        null=False,
        blank=False
    )
    cooking_time = models.IntegerField(verbose_name='Время приготовления')

    class Meta:
        ordering = ('id',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def _str_(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.SmallIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'

    def __str__(self):
        return (f'{self.ingredient.name} - {self.amount}'
                f' {self.ingredient.measurement_unit}')


class Favorite(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='favorited_by'
    )

    class Meta:
        unique_together = ('user', 'recipe')
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='shopping_cart'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='in_carts'
    )

    class Meta:
        unique_together = ('user', 'recipe')
