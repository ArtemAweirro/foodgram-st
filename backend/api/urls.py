from rest_framework import routers
from django.urls import include, path

from api.views import (
    RecipeViewSet, IngredientViewSet,
    CustomUserViewSet
)


router = routers.DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),  # Работа с токенами
]
