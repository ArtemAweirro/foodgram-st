import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MinValueValidator


class Ingredient(models.Model):
    name = models.CharField(verbose_name='Название', max_length=128)
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=64
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class User(AbstractUser):
    email = models.EmailField(
        unique=True,
        max_length=254,
        verbose_name='Почта'
    )
    username = models.CharField(
        unique=True,
        max_length=150,
        validators=(UnicodeUsernameValidator(),),
        verbose_name='Никнейм'
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия'
    )
    avatar = models.ImageField(
        upload_to='users/images/',
        null=True,
        blank=True,
        verbose_name='Аватар'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


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
        related_name='recipes',
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
        validators=(MinValueValidator(1),)
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class ShortLink(models.Model):
    slug = models.SlugField(
        unique=True,
        max_length=64,
        verbose_name='Короткий код'
    )
    original_url = models.URLField(
        verbose_name='Оригинальная ссылка'
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Короткая ссылка'
        verbose_name_plural = 'Короткие ссылки'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuid.uuid4().hex[:7]
        super().save(*args, **kwargs)

    def __str__(self):
        return f'/s/{self.slug} → {self.original_url}'


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
        validators=(MinValueValidator(1),)
    )

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'

    def __str__(self):
        return (f'{self.recipe.name} - {self.ingredient.name} - {self.amount}'
                f' {self.ingredient.measurement_unit}')


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        related_name='followers',
        on_delete=models.CASCADE,
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        related_name='authors',
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )

    class Meta:
        ordering = ('author',)
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_subscription'
            ),
        )


class Favorite(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт'
    )

    class Meta:
        unique_together = ('user', 'recipe')
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite'
            ),
        )

    def __str__(self):
        return f'{self.user} - {self.recipe}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='shopping_carts'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='in_carts'
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shopping_cart'
            ),
        )

    def __str__(self):
        return f'{self.user} - {self.recipe}'
