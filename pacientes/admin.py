from django.contrib import admin
from .models import PerfilPaciente


@admin.register(PerfilPaciente)
class PerfilPacienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'sexo', 'fecha_nacimiento', 'telefono', 'created_at')
    search_fields = ('usuario__nombre', 'usuario__apellido', 'usuario__correo')
    list_filter = ('sexo',)
