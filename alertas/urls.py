from django.urls import path
from . import views

app_name = 'alertas'

urlpatterns = [
    path('', views.lista_alertas, name='lista'),
    path('marcar/<int:pk>/', views.marcar_leida, name='marcar_leida'),
    path('marcar-todas/', views.marcar_todas_leidas, name='marcar_todas'),
    path('api/count/', views.api_alertas_count, name='api_count'),
]
