from django.urls import path
from . import views

app_name = 'prediccion'

urlpatterns = [
    path('nueva/<int:datos_pk>/', views.nueva_prediccion, name='nueva'),
    path('resultado/<int:pk>/', views.resultado, name='resultado'),
    path('historial/', views.historial_predicciones, name='historial'),
]
