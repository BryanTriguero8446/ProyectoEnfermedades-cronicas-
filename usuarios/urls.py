from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # HTML Views (Frontend)
    path('', views.index_view, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('estadisticas/', views.estadisticas_view, name='estadisticas'),

    # Verificación de correo
    path('verificar-codigo/', views.verificacion_enviada_view, name='verificacion_enviada'),
    path('reenviar-verificacion/', views.reenviar_verificacion_view, name='reenviar_verificacion'),

    # API REST
    path('api/me/', views.obtener_perfil, name='api_perfil'),
]