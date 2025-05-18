from django.contrib import admin

from .models import Recipe, Ingredient


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'text')


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')


# class UserAdmin
# UserAdmin.fieldsets += (
#     ('Extra Fields', {'fields': ('bio',)}),
# )


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
