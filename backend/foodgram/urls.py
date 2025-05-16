from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework import routers

from api.views import RecipeViewSet


router = routers.DefaultRouter()
router.register(r'recipes', RecipeViewSet, basename='recipe')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/', include('djoser.urls')),  # Работа с пользователями
    path('api/auth/', include('djoser.urls.authtoken')),  # Работа с токенами
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
