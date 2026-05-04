from django.db import models
from usuarios.models import Usuario


class PerfilPaciente(models.Model):
    SEXO_CHOICES = [('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')]

    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil')
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    ocupacion = models.CharField(max_length=100, blank=True)
    antecedentes_familiares = models.TextField(blank=True)
    alergias = models.TextField(blank=True)
    foto = models.ImageField(upload_to='fotos_pacientes/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'perfil_paciente'
        verbose_name = 'Perfil de Paciente'

    def __str__(self):
        return f"Perfil de {self.usuario}"

    @property
    def edad(self):
        from datetime import date
        if self.fecha_nacimiento:
            hoy = date.today()
            return hoy.year - self.fecha_nacimiento.year - (
                (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None
