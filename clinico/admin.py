from django.contrib import admin
from .models import DatosClinico, HistorialAccesos, HistorialClinico


@admin.register(DatosClinico)
class DatosClinicoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'glucosa', 'presion_sistolica', 'presion_diastolica', 'imc', 'fecha_registro')
    list_filter = ('actividad_fisica', 'fumador', 'alcohol')
    search_fields = ('paciente__nombre', 'paciente__apellido', 'paciente__correo')
    date_hierarchy = 'fecha_registro'
    readonly_fields = ('imc', 'fecha_registro')


@admin.register(HistorialAccesos)
class HistorialAccesosAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'accion', 'ip', 'fecha_hora')
    list_filter = ('accion',)
    date_hierarchy = 'fecha_hora'


@admin.register(HistorialClinico)
class HistorialClinicoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'tipo', 'fecha', 'creado_por')
    list_filter = ('tipo',)
