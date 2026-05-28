from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario


SEXO_CHOICES_REGISTRO = [
    ('', '-- Seleccionar --'),
    ('M', 'Hombre'),
    ('F', 'Mujer'),
    ('O', 'Prefiero no decirlo'),
]


class RegistroForm(UserCreationForm):
    correo   = forms.EmailField(required=True)
    nombre   = forms.CharField(max_length=100, required=True)
    apellido = forms.CharField(max_length=100, required=True)
    sexo     = forms.ChoiceField(choices=SEXO_CHOICES_REGISTRO, required=False)

    class Meta:
        model  = Usuario
        fields = ('correo', 'nombre', 'apellido', 'password1', 'password2')

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if Usuario.objects.filter(correo=correo).exists():
            raise forms.ValidationError('Este correo ya está registrado.')
        return correo