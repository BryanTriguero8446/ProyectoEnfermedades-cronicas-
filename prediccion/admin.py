from django.contrib import admin
from .models import Prediccion


@admin.register(Prediccion)
class PrediccionAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'nivel_general', 'riesgo_diabetes', 'riesgo_hipertension',
                    'riesgo_cardiaco', 'modelo_version', 'fecha_prediccion')
    list_filter = ('nivel_diabetes', 'nivel_cardiaco', 'modelo_version')
    search_fields = ('paciente__nombre', 'paciente__apellido')
    date_hierarchy = 'fecha_prediccion'
    readonly_fields = ('fecha_prediccion',)
