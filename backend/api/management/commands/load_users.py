import json
import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Загрузка пользователей из файла users.json'

    def handle(self, *args, **options):
        file_path = os.path.join('data', 'users.json')

        with open(file_path, 'r', encoding='utf-8') as file:
            users = json.load(file)

        for user_data in users:
            if not User.objects.filter(
                username=user_data['username']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    password=user_data['password']
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Создан пользователь: {user.username}'))
            else:
                self.stdout.write(
                    f'Пользователь {user_data["username"]} уже существует')
