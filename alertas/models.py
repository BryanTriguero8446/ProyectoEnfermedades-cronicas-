from django.db import models
from usuarios.models import Usuario


class Alerta(models.Model):
    TIPO_CHOICES = [
        ('glucosa_alta', 'Glucosa Alta'),
        ('glucosa_baja', 'Glucosa Baja'),
        ('presion_alta', 'Presión Alta'),
        ('imc_alto', 'IMC Alto'),
        ('imc_bajo', 'IMC Bajo'),
        ('frecuencia_anormal', 'Frecuencia Cardíaca Anormal'),
        ('riesgo_alto_diabetes', 'Riesgo Alto - Diabetes'),
        ('riesgo_alto_hipertension', 'Riesgo Alto - Hipertensión'),
        ('riesgo_alto_renal', 'Riesgo Alto - Renal'),
        ('riesgo_alto_nafld', 'Riesgo Alto - Hígado Graso'),
        ('riesgo_alto_cardiaco', 'Riesgo Alto - Cardíaco'),
    ]
    SEVERIDAD_CHOICES = [
        ('info', 'Informativo'),
        ('warning', 'Advertencia'),
        ('danger', 'Crítico'),
    ]

    paciente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='alertas')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    severidad = models.CharField(max_length=10, choices=SEVERIDAD_CHOICES, default='warning')
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    datos_clinicos = models.ForeignKey(
        'clinico.DatosClinico', on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        db_table = 'alerta'
        ordering = ['-fecha_creacion']
        verbose_name = 'Alerta'

    def __str__(self):
        return f"[{self.severidad.upper()}] {self.paciente} - {self.tipo}"

    @property
    def icono(self):
        iconos = {
            'info': 'bi-info-circle',
            'warning': 'bi-exclamation-triangle',
            'danger': 'bi-exclamation-octagon',
        }
        return iconos.get(self.severidad, 'bi-bell')

    @property
    def color_badge(self):
        colores = {'info': 'primary', 'warning': 'warning', 'danger': 'danger'}
        return colores.get(self.severidad, 'secondary')
