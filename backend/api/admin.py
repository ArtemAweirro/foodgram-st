from django.contrib import admin

from .models import (
    Recipe, Ingredient, RecipeIngredient,
    User, Subscription, Favorite, ShoppingCart
)


admin.site.empty_value_display = 'Не задано'


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1  # Количество пустых строк по умолчанию
    autocomplete_fields = ('ingredient',)


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author')
    readonly_fields = ('favorites_count',)
    search_fields = ('name', 'author')
    list_filter = ('author',)
    inlines = (RecipeIngredientInline,)
    filter_horizontal = ('ingredients',)

    @admin.display(description='Количество в избранном')
    def favorites_count(self, obj):
        return obj.favorited_by.count()


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email')
    search_fields = ('first_name', 'last_name', 'username', 'email')


class SubcriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user',)
    list_filter = ('user', 'author')


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user',)
    list_filter = ('user', 'recipe')


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user',)
    list_filter = ('user',)


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(RecipeIngredient, RecipeIngredientAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Subscription, SubcriptionAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
