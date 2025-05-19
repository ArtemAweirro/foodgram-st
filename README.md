# Foodgram

Foodgram — «Продуктовый помощник»: приложение для публикации рецептов, добавления их в избранное и список покупок, а также подписки на авторов.

## 🚀 Подготовка к запуску проекта

Выполните клонирование репозитория:

```bash
git clone https://github.com/ArtemAweirro/foodgram-st.git
```
```bash
cd foodgram-st
```
В корне проекта разместите .env файл. Структура:
```
POSTGRES_USER=django_user
POSTGRES_PASSWORD=mysecretpassword
POSTGRES_DB=django
DB_HOST=db
DB_PORT=5432
```
### Соберите и запустите проект:
```bash
cd infra
```
```bash
docker-compose up -d --build
```
Далее откройте новое окно терминала и в нем примените миграции:

```bash
docker-compose exec backend python manage.py migrate
```

Соберите статику:
```bash
docker-compose exec backend python manage.py collectstatic --noinput
```
Создайте суперпользователя:
```bash
docker-compose exec backend python manage.py createsuperuser
```

На данном этапе проект уже работает, но он пуст. Чтобы заполнить его данными, загрузите ингредиенты, пользователей и рецепты:

```bash
docker-compose exec backend python manage.py load_ingredients
```
```bash
docker-compose exec backend python manage.py load_users
```
```bash
docker-compose exec backend python manage.py load_recipes
```

Приятного пользования!