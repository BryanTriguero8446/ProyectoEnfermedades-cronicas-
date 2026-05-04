from django.urls import path
from . import views

app_name = 'pacientes'

urlpatterns = [
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
]
