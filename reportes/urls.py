from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.lista_reportes, name='lista'),
    path('csv/clinico/', views.generar_csv, name='csv_clinico'),
    path('csv/predicciones/', views.generar_csv_predicciones, name='csv_predicciones'),
]
