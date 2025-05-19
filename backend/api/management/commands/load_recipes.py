import json
import os
from django.core.management.base import BaseCommand
from django.core.files.images import ImageFile
from api.models import Recipe, Ingredient, RecipeIngredient, User


class Command(BaseCommand):
    help = 'Загрузка рецептов из файла recipes.json'

    def handle(self, *args, **options):
        file_path = os.path.join('data', 'recipes.json')

        with open(file_path, 'r', encoding='utf-8') as file:
            recipes = json.load(file)

        for recipe_data in recipes:
            author = User.objects.filter(
                username=recipe_data['author']).first()
            if not author:
                self.stdout.write(
                    self.style.ERROR(
                        f"Автор {recipe_data['author']} не найден."))
                continue

            recipe = Recipe.objects.create(
                name=recipe_data['name'],
                text=recipe_data['text'],
                cooking_time=recipe_data['cooking_time'],
                author=author
            )

            if recipe_data.get('image'):
                image_path = os.path.join('data', recipe_data['image'])
                with open(image_path, 'rb') as img_file:
                    recipe.image.save(os.path.basename(image_path), ImageFile(img_file), save=True)

            for ingredient_info in recipe_data['ingredients']:
                ingredient = Ingredient.objects.filter(name=ingredient_info['name']).first()
                if ingredient:
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        ingredient=ingredient,
                        amount=ingredient_info['amount']
                    )
            self.stdout.write(self.style.SUCCESS(f'Создан рецепт: {recipe.name}'))
