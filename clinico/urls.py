from django.urls import path
from . import views

app_name = 'clinico'

urlpatterns = [
    path('nuevo/', views.nuevo_registro, name='nuevo_registro'),
    path('historial/', views.historial, name='historial'),
    path('detalle/<int:pk>/', views.detalle, name='detalle'),
    path('api/historial/', views.api_historial_json, name='api_historial'),
]
