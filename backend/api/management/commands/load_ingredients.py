import json
import os
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.db.utils import OperationalError
from api.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из ingredients.json'

    def handle(self, *args, **kwargs):
        try:
            path = os.path.join('data', 'ingredients.json')
            with open(path, encoding='utf-8') as file:
                data = json.load(file)

            new_ingredients = []
            for item in data:
                new_ingredients.append(Ingredient(**item))

            Ingredient.objects.bulk_create(new_ingredients)

            self.stdout.write(
                self.style.SUCCESS(
                    f'{len(new_ingredients)} ингредиентов успешно загружено.'
                )
            )

        except FileNotFoundError:
            self.stderr.write(
                self.style.ERROR('Файл ingredients.json не найден.')
            )
        except json.JSONDecodeError:
            self.stderr.write(
                self.style.ERROR('Ошибка чтения JSON-файла.')
            )
        except (IntegrityError, OperationalError) as e:
            self.stderr.write(
                self.style.ERROR(f'Ошибка базы данных: {e}')
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Произошла непредвиденная ошибка: {e}')
            )
