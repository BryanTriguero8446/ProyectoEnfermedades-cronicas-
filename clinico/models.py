from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from usuarios.models import Usuario


class HistorialAccesos(models.Model):
    ACCION_CHOICES = [
        ('login_ok', 'Inicio de sesión exitoso'),
        ('login_fail', 'Intento fallido'),
        ('logout', 'Cierre de sesión'),
    ]
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='accesos')
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historial_accesos'
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"{self.id_usuario} - {self.accion} - {self.fecha_hora}"


class DatosClinico(models.Model):
    ACTIVIDAD_CHOICES = [
        ('sedentario', 'Sedentario'),
        ('leve', 'Actividad leve'),
        ('moderado', 'Moderado'),
        ('activo', 'Activo'),
        ('muy_activo', 'Muy activo'),
    ]

    paciente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='datos_clinicos')
    edad = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(120)])
    peso = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(1)])
    altura = models.DecimalField(max_digits=4, decimal_places=2, validators=[MinValueValidator(0.5)])
    imc = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    presion_sistolica = models.PositiveIntegerField(validators=[MinValueValidator(50), MaxValueValidator(300)])
    presion_diastolica = models.PositiveIntegerField(validators=[MinValueValidator(30), MaxValueValidator(200)])
    glucosa = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(10)])
    frecuencia_cardiaca = models.PositiveIntegerField(validators=[MinValueValidator(30), MaxValueValidator(300)])
    colesterol = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    trigliceridos = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    creatinina = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    actividad_fisica = models.CharField(max_length=20, choices=ACTIVIDAD_CHOICES, default='sedentario')
    fumador = models.BooleanField(default=False)
    alcohol = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'datos_clinicos'
        ordering = ['-fecha_registro']
        verbose_name = 'Datos Clínicos'

    def __str__(self):
        return f"Registro {self.pk} - {self.paciente} - {self.fecha_registro.date()}"

    def save(self, *args, **kwargs):
        if self.peso and self.altura and float(self.altura) > 0:
            self.imc = round(float(self.peso) / (float(self.altura) ** 2), 2)
        super().save(*args, **kwargs)

    @property
    def clasificacion_imc(self):
        if not self.imc:
            return 'Sin dato'
        imc = float(self.imc)
        if imc < 18.5:
            return 'Bajo peso'
        elif imc < 25:
            return 'Normal'
        elif imc < 30:
            return 'Sobrepeso'
        elif imc < 35:
            return 'Obesidad I'
        elif imc < 40:
            return 'Obesidad II'
        return 'Obesidad III'

    @property
    def clasificacion_glucosa(self):
        g = float(self.glucosa)
        if g < 70:
            return ('baja', 'warning')
        elif g <= 100:
            return ('normal', 'success')
        elif g <= 125:
            return ('prediabetes', 'warning')
        return ('alta', 'danger')

    @property
    def clasificacion_presion(self):
        s, d = self.presion_sistolica, self.presion_diastolica
        if s < 120 and d < 80:
            return ('normal', 'success')
        elif s < 130 and d < 80:
            return ('elevada', 'warning')
        elif s < 140 or d < 90:
            return ('hipertensión I', 'warning')
        return ('hipertensión II', 'danger')


class HistorialClinico(models.Model):
    TIPO_CHOICES = [
        ('general', 'Nota general'),
        ('seguimiento', 'Seguimiento'),
        ('alerta', 'Alerta'),
        ('resultado', 'Resultado'),
    ]
    paciente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='historial_clinico')
    datos_clinicos = models.ForeignKey(DatosClinico, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='general')
    nota = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True,
        related_name='notas_creadas'
    )

    class Meta:
        db_table = 'historial_clinico'
        ordering = ['-fecha']
