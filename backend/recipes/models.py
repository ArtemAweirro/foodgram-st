from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

User = get_user_model()


class Ingredient(models.Model):
    name = models.CharField(verbose_name='Название', max_length=128)
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=64
    )

    class Meta:
        ordering = ('id',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='ingredient_in_recipes',
        verbose_name='Ингредиенты'
    )
    name = models.CharField(verbose_name='Название', max_length=256)
    text = models.TextField(verbose_name='Описание')
    image = models.ImageField(
        upload_to='recipe/images/',
        null=False,
        blank=False,
        verbose_name='Изображение'
    )
    cooking_time = models.IntegerField(
        verbose_name='Время приготовления',
        validators=(
            MinValueValidator(
                1, 'Время приготовления должно быть не менее 1 минуты'
            ),
        )
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Ингредиент'
    )
    amount = models.SmallIntegerField(
        verbose_name='Количество',
        validators=(
            MinValueValidator(
                1, 'Количество ингредиентов должно быть не менее 1 ед.'
            ),
        )
    )

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'

    def __str__(self):
        return (f'{self.recipe.name} - {self.ingredient.name} - {self.amount}'
                f' {self.ingredient.measurement_unit}')
