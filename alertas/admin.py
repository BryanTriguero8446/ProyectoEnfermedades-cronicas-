from django.contrib import admin
from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'tipo', 'severidad', 'leida', 'fecha_creacion')
    list_filter = ('severidad', 'leida', 'tipo')
    search_fields = ('paciente__nombre', 'paciente__apellido')
    date_hierarchy = 'fecha_creacion'
    actions = ['marcar_leidas']

    @admin.action(description='Marcar seleccionadas como leídas')
    def marcar_leidas(self, request, queryset):
        queryset.update(leida=True)
