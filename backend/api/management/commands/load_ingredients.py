import json
from django.core.management.base import BaseCommand
from api.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из ingredients.json'

    def handle(self, *args, **kwargs):
        with open('data/ingredients.json', encoding='utf-8') as file:
            data = json.load(file)
            count = 0
            for item in data:
                obj, created = Ingredient.objects.get_or_create(
                    name=item['name'],
                    measurement_unit=item['measurement_unit']
                )
                if created:
                    count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'{count} ingredients successfully loaded.'))
