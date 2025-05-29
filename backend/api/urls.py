from rest_framework import routers
from django.urls import include, path

from api.views import UserViewSet, RecipeViewSet, IngredientViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),  # Работа с токенами
]
