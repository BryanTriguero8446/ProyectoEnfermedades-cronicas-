from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import DatosClinico, HistorialClinico
from alertas.models import Alerta


@login_required(login_url='usuarios:login')
def nuevo_registro(request):
    """Formulario para ingresar nuevos datos clínicos."""
    if request.method == 'POST':
        try:
            datos = DatosClinico(
                paciente=request.user,
                edad=int(request.POST.get('edad')),
                peso=float(request.POST.get('peso')),
                altura=float(request.POST.get('altura')),
                presion_sistolica=int(request.POST.get('presion_sistolica')),
                presion_diastolica=int(request.POST.get('presion_diastolica')),
                glucosa=float(request.POST.get('glucosa')),
                frecuencia_cardiaca=int(request.POST.get('frecuencia_cardiaca')),
                actividad_fisica=request.POST.get('actividad_fisica', 'sedentario'),
                fumador=request.POST.get('fumador') == 'on',
                alcohol=request.POST.get('alcohol') == 'on',
                observaciones=request.POST.get('observaciones', ''),
            )
            col = request.POST.get('colesterol', '').strip()
            tri = request.POST.get('trigliceridos', '').strip()
            cre = request.POST.get('creatinina', '').strip()
            if col:
                datos.colesterol = float(col)
            if tri:
                datos.trigliceridos = float(tri)
            if cre:
                datos.creatinina = float(cre)

            datos.save()

            # Generar alertas automáticas
            from prediccion.service import generar_alertas
            alertas_data = generar_alertas(datos, {})
            for a in alertas_data:
                Alerta.objects.create(
                    paciente=request.user,
                    tipo=a['tipo'],
                    severidad=a['severidad'],
                    mensaje=a['mensaje'],
                    datos_clinicos=datos,
                )

            messages.success(request, 'Datos clínicos registrados correctamente.')
            return redirect('clinico:detalle', pk=datos.pk)
        except (ValueError, TypeError) as e:
            messages.error(request, f'Error en los datos ingresados: {e}')

    return render(request, 'clinico/nuevo_registro.html')


@login_required(login_url='usuarios:login')
def historial(request):
    """Lista de todos los registros clínicos del paciente."""
    registros = DatosClinico.objects.filter(paciente=request.user)
    return render(request, 'clinico/historial.html', {'registros': registros})


@login_required(login_url='usuarios:login')
def detalle(request, pk):
    """Detalle de un registro clínico específico."""
    registro = get_object_or_404(DatosClinico, pk=pk, paciente=request.user)
    predicciones = registro.predicciones.all()
    alertas = Alerta.objects.filter(datos_clinicos=registro)
    return render(request, 'clinico/detalle.html', {
        'registro': registro,
        'predicciones': predicciones,
        'alertas': alertas,
    })


@login_required(login_url='usuarios:login')
def api_historial_json(request):
    """API: Retorna últimos 10 registros como JSON para gráficos."""
    registros = DatosClinico.objects.filter(
        paciente=request.user
    ).order_by('fecha_registro')[:20]

    data = {
        'labels': [r.fecha_registro.strftime('%d/%m/%y') for r in registros],
        'glucosa': [float(r.glucosa) for r in registros],
        'presion_sistolica': [r.presion_sistolica for r in registros],
        'presion_diastolica': [r.presion_diastolica for r in registros],
        'imc': [float(r.imc) if r.imc else 0 for r in registros],
        'frecuencia_cardiaca': [r.frecuencia_cardiaca for r in registros],
    }
    return JsonResponse(data)
