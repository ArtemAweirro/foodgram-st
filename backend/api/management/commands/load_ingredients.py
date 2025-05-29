import json
import os
from django.core.management.base import BaseCommand
from api.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из ingredients.json'

    def handle(self, *args, **kwargs):
        try:
            path = os.path.join('data', 'ingredients.json')
            with open(path, encoding='utf-8') as file:
                Ingredient.objects.bulk_create(
                    (Ingredient(**item) for item in json.load(file)),
                    ignore_conflicts=True
                )

            self.stdout.write(
                self.style.SUCCESS(
                    # Предполагается, что метод вызывается разово
                    # при первом запуске проекта => БД первоначально пуста
                    (f'{Ingredient.objects.count()}'
                     ' ингредиентов успешно загружено.')
                )
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(
                    'Произошла непредвиденная ошибка при обработке файла '
                    f'"{path}": {e}'
                )
            )
