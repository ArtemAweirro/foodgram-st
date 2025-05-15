from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    email = models.EmailField(unique=True)
    avatar = models.ImageField(
        upload_to='users/images/',
        null=True,
        blank=True,
        verbose_name='Аватар'
    )

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    USERNAME_FIELD = 'username'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Ingredient(models.Model):
    name = models.CharField(verbose_name='Название', max_length=100)
    measurement_unit = models.CharField(verbose_name='Единица измерения', max_length=50)
    amount = models.SmallIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def _str_(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты'
    )
    is_favorited = models.BooleanField(verbose_name='Понравившееся')
    is_in_shooping_cart = models.BooleanField(verbose_name='В корзине')
    name = models.CharField(verbose_name='Название', max_length=255)
    text = models.TextField(verbose_name='Описание')
    image = models.ImageField(
        upload_to='recipe/images/',
        null=True,
        default=None
    )
    cooking_time = models.SmallIntegerField(verbose_name='Время приготовления')

    class Meta:
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
