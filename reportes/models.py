from django.db import models
from usuarios.models import Usuario


class Reporte(models.Model):
    FORMATO_CHOICES = [('pdf', 'PDF'), ('csv', 'CSV')]
    TIPO_CHOICES = [
        ('clinico', 'Historial Clínico'),
        ('prediccion', 'Predicciones'),
        ('completo', 'Reporte Completo'),
    ]
    ESTADO_CHOICES = [
        ('generando', 'Generando'),
        ('listo', 'Listo'),
        ('error', 'Error'),
    ]

    paciente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='reportes')
    formato = models.CharField(max_length=5, choices=FORMATO_CHOICES, default='pdf')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='completo')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='generando')
    archivo = models.FileField(upload_to='reportes/', null=True, blank=True)
    generado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True,
        related_name='reportes_generados'
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    parametros = models.JSONField(default=dict)

    class Meta:
        db_table = 'reporte'
        ordering = ['-fecha_generacion']
        verbose_name = 'Reporte'

    def __str__(self):
        return f"Reporte {self.tipo} ({self.formato}) - {self.paciente} - {self.fecha_generacion.date()}"
