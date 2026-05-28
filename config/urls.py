from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),
    path('clinico/', include('clinico.urls')),
    path('prediccion/', include('prediccion.urls')),
    path('alertas/', include('alertas.urls')),
    path('paciente/', include('pacientes.urls')),
    path('reportes/', include('reportes.urls')),
    # JWT — obtener y refrescar tokens
    path('api/token/',         TokenObtainPairView.as_view(),  name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(),     name='token_refresh'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
