from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PerfilPaciente


@login_required(login_url='usuarios:login')
def perfil(request):
    perfil_obj, _ = PerfilPaciente.objects.get_or_create(usuario=request.user)
    return render(request, 'pacientes/perfil.html', {'perfil': perfil_obj})


@login_required(login_url='usuarios:login')
def editar_perfil(request):
    perfil_obj, _ = PerfilPaciente.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        u = request.user
        u.nombre = request.POST.get('nombre', u.nombre).strip()
        u.apellido = request.POST.get('apellido', u.apellido).strip()
        u.save()

        perfil_obj.telefono = request.POST.get('telefono', '').strip()
        perfil_obj.direccion = request.POST.get('direccion', '').strip()
        perfil_obj.ocupacion = request.POST.get('ocupacion', '').strip()
        perfil_obj.antecedentes_familiares = request.POST.get('antecedentes_familiares', '').strip()
        perfil_obj.alergias = request.POST.get('alergias', '').strip()
        perfil_obj.sexo = request.POST.get('sexo', '').strip()

        fecha_nac = request.POST.get('fecha_nacimiento', '').strip()
        if fecha_nac:
            from datetime import date
            try:
                perfil_obj.fecha_nacimiento = date.fromisoformat(fecha_nac)
            except ValueError:
                pass

        if request.FILES.get('foto'):
            perfil_obj.foto = request.FILES['foto']

        perfil_obj.save()
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('pacientes:perfil')

    return render(request, 'pacientes/editar_perfil.html', {'perfil': perfil_obj})
