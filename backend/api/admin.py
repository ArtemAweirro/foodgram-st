from django.contrib import admin
from django.utils.safestring import mark_safe
from django.db.models import Count, Prefetch

from .models import (
    Recipe, User, Subscription, Favorite, ShoppingCart,
    Ingredient, RecipeIngredient
)


admin.site.empty_value_display = 'Не задано'


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1  # Количество пустых строк по умолчанию
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'cooking_time', 'author',
                    'favorites_count', 'display_ingredients', 'display_image')
    readonly_fields = ('favorites_count',)
    search_fields = ('name', 'author')
    list_filter = ('author',)
    inlines = (RecipeIngredientInline,)
    filter_horizontal = ('ingredients',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        # Аннотируем количество добавлений рецепта в избранное
        queryset = queryset.annotate(
            fav_count=Count('favorites', distinct=True)
        )

        # Предзагружаем ингредиенты через связь RecipeIngredient и ingredient
        queryset = queryset.prefetch_related(
            Prefetch(
                'recipe_ingredients',
                queryset=RecipeIngredient.objects.select_related('ingredient')
            )
        )
        return queryset

    @admin.display(description='Количество в избранном')
    def favorites_count(self, recipe):
        return recipe.fav_count

    @admin.display(description='Ингредиенты')
    def display_ingredients(self, recipe):
        # Используем уже предзагруженные RecipeIngredient объекты
        recipe_ingredients = recipe.recipe_ingredients.all()
        return mark_safe(
            '<br>'.join(
                (f'{ri.ingredient.name} — {ri.amount} '
                 f'{ri.ingredient.measurement_unit}')
                for ri in recipe_ingredients
            )
        )

    @admin.display(description='Картинка')
    def display_image(self, recipe):
        if recipe.image:
            return mark_safe(
                f'<img src="{recipe.image.url}" width="100" height="100" />')
        return 'Нет изображения'


class InRecipesFilter(admin.SimpleListFilter):
    title = 'Есть в рецептах'
    parameter_name = 'in_recipes'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(recipe_ingredients__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(recipe_ingredients__isnull=True)
        return queryset


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit', 'recipes_count')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit', InRecipesFilter)

    @admin.display(description='Количество рецептов с данным ингредиентом')
    def recipes_count(self, ingredient):
        return ingredient.recipes_count

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            recipes_count=Count('recipe_ingredients__recipe', distinct=True)
        )


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')


class HasRecipesFilter(admin.SimpleListFilter):
    title = 'Есть рецепты'
    parameter_name = 'has_recipes'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(recipes__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(recipes__isnull=True)
        return queryset


class HasSubscriptionsFilter(admin.SimpleListFilter):
    title = 'Есть подписчики'
    parameter_name = 'has_subscriptions'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(following__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(following__isnull=True)
        return queryset


class HasSubscribersFilter(admin.SimpleListFilter):
    title = 'Есть подписки'
    parameter_name = 'has_subscribers'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(follower__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(follower__isnull=True)
        return queryset


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'display_name', 'email',
                    'display_avatar', 'recipe_count',
                    'subscribe_count', 'subscription_count',
                    )
    search_fields = ('first_name', 'last_name', 'username', 'email')
    list_filter = (
        HasRecipesFilter, HasSubscriptionsFilter, HasSubscribersFilter)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            recipe_count=Count('recipes', distinct=True),
            subscription_count=Count('authors', distinct=True),  # на него
            subscribe_count=Count('followers', distinct=True)  # на других
        )

    @admin.display(description='Фамилия Имя')
    def display_name(self, user):
        return f'{user.last_name} {user.first_name}'

    @admin.display(description='Аватар')
    def display_avatar(self, user):
        if user.avatar:
            return mark_safe(
                f'<img src="{user.avatar.url}" width="50" height="50" />')
        return 'Нет аватарки'

    @admin.display(description='Рецептов')
    def recipe_count(self, user):
        return user.recipe_count

    @admin.display(description='Подписок')
    def subscribe_count(self, user):
        return user.subscribe_count

    @admin.display(description='Подписчиков')
    def subscription_count(self, user):
        return user.subscription_count


@admin.register(Subscription)
class SubcriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user',)
    list_filter = ('user', 'author')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user',)
    list_filter = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user',)
    list_filter = ('user',)
