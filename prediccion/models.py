from django.db import models
from usuarios.models import Usuario


class Prediccion(models.Model):
    NIVEL_CHOICES = [('bajo', 'Bajo'), ('medio', 'Medio'), ('alto', 'Alto')]

    paciente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='predicciones')
    datos_clinicos = models.ForeignKey(
        'clinico.DatosClinico', on_delete=models.CASCADE,
        related_name='predicciones'
    )

    # Diabetes Tipo 2
    riesgo_diabetes = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    nivel_diabetes = models.CharField(max_length=10, choices=NIVEL_CHOICES, default='bajo')

    # Hipertensión
    riesgo_hipertension = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    nivel_hipertension = models.CharField(max_length=10, choices=NIVEL_CHOICES, default='bajo')

    # Enfermedad Renal Crónica
    riesgo_renal = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    nivel_renal = models.CharField(max_length=10, choices=NIVEL_CHOICES, default='bajo')

    # Hígado Graso No Alcohólico
    riesgo_nafld = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    nivel_nafld = models.CharField(max_length=10, choices=NIVEL_CHOICES, default='bajo')

    # Insuficiencia Cardíaca
    riesgo_cardiaco = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    nivel_cardiaco = models.CharField(max_length=10, choices=NIVEL_CHOICES, default='bajo')

    modelo_version = models.CharField(max_length=30, default='rule_based_v1')
    fecha_prediccion = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True)

    class Meta:
        db_table = 'prediccion'
        ordering = ['-fecha_prediccion']
        verbose_name = 'Predicción'

    def __str__(self):
        return f"Predicción {self.pk} - {self.paciente} - {self.fecha_prediccion.date()}"

    @property
    def riesgo_maximo(self):
        riesgos = [
            (float(self.riesgo_diabetes), 'Diabetes'),
            (float(self.riesgo_hipertension), 'Hipertensión'),
            (float(self.riesgo_renal), 'Renal'),
            (float(self.riesgo_nafld), 'Hígado Graso'),
            (float(self.riesgo_cardiaco), 'Cardíaco'),
        ]
        return max(riesgos, key=lambda x: x[0])

    @property
    def nivel_general(self):
        niveles = [self.nivel_diabetes, self.nivel_hipertension,
                   self.nivel_renal, self.nivel_nafld, self.nivel_cardiaco]
        if 'alto' in niveles:
            return 'alto'
        if 'medio' in niveles:
            return 'medio'
        return 'bajo'
