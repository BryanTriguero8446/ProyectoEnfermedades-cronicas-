from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UsuarioManager(BaseUserManager):
    def create_user(self, correo, nombre, apellido, password=None, **extra):
        if not correo:
            raise ValueError('El correo es obligatorio')
        user = self.model(correo=self.normalize_email(correo.lower()),
                         nombre=nombre, apellido=apellido, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo, nombre, apellido, password):
        user = self.create_user(correo, nombre, apellido, password)
        user.is_staff = True
        user.is_superuser = True
        user.rol = 'administrador'
        user.save(using=self._db)
        return user

class Usuario(AbstractBaseUser, PermissionsMixin):
    ROL_CHOICES = [('paciente', 'Paciente'), ('administrador', 'Administrador')]
    
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    correo = models.EmailField(unique=True)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='paciente')
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    is_staff = models.BooleanField(default=False)
    intentos_fallidos = models.IntegerField(default=0)
    bloqueado = models.BooleanField(default=False)

    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre', 'apellido']
    objects = UsuarioManager()

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.correo})"
