from django.contrib import admin
from .models import Reporte


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'tipo', 'formato', 'estado', 'fecha_generacion')
    list_filter = ('tipo', 'formato', 'estado')
    search_fields = ('paciente__nombre', 'paciente__apellido')
    date_hierarchy = 'fecha_generacion'
