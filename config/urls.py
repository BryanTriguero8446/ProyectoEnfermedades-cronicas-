from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),
    path('clinico/', include('clinico.urls')),
    path('prediccion/', include('prediccion.urls')),
    path('alertas/', include('alertas.urls')),
    path('paciente/', include('pacientes.urls')),
    path('reportes/', include('reportes.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
