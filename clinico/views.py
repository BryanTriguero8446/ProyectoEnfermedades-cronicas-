from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import DatosClinico, HistorialClinico
from alertas.models import Alerta


def _poblar_datos(datos, post):
    """Asigna campos de un POST a una instancia de DatosClinico."""
    datos.edad               = int(post.get('edad'))
    datos.peso               = Decimal(post.get('peso'))
    datos.altura             = Decimal(post.get('altura'))
    datos.presion_sistolica  = int(post.get('presion_sistolica'))
    datos.presion_diastolica = int(post.get('presion_diastolica'))
    datos.glucosa            = Decimal(post.get('glucosa'))
    datos.frecuencia_cardiaca= int(post.get('frecuencia_cardiaca'))
    datos.actividad_fisica   = post.get('actividad_fisica', 'sedentario')
    datos.fumador            = post.get('fumador') == 'on'
    datos.alcohol            = post.get('alcohol') == 'on'
    datos.observaciones      = post.get('observaciones', '')
    # Antecedentes familiares (checkboxes)
    datos.antec_diabetes_uno   = post.get('antec_diabetes_uno')   == 'on'
    datos.antec_diabetes_ambos = post.get('antec_diabetes_ambos') == 'on'
    datos.antec_hta_uno        = post.get('antec_hta_uno')        == 'on'
    datos.antec_hta_ambos      = post.get('antec_hta_ambos')      == 'on'
    datos.antec_renal          = post.get('antec_renal')          == 'on'
    datos.antec_nafld          = post.get('antec_nafld')          == 'on'
    datos.antec_cardiaco       = post.get('antec_cardiaco')       == 'on'
    col = post.get('colesterol', '').strip()
    tri = post.get('trigliceridos', '').strip()
    cre = post.get('creatinina', '').strip()
    datos.colesterol    = Decimal(col) if col else None
    datos.trigliceridos = Decimal(tri) if tri else None
    datos.creatinina    = Decimal(cre) if cre else None


@login_required(login_url='usuarios:login')
def nuevo_registro(request):
    """Formulario para ingresar nuevos datos clínicos (sólo pacientes)."""
    # Administradores no pueden crear registros clínicos
    if request.user.rol == 'administrador':
        messages.warning(request, 'Los administradores no tienen permiso para crear registros clínicos.')
        return redirect('usuarios:dashboard')

    if request.method == 'POST':
        try:
            datos = DatosClinico(paciente=request.user)
            _poblar_datos(datos, request.POST)
            datos.full_clean()
            datos.save()
            _crear_alertas_clinicas(request.user, datos)
            messages.success(request, 'Datos clínicos registrados correctamente.')
            return redirect('clinico:detalle', pk=datos.pk)
        except Exception as e:
            _manejar_error_validacion(request, e)

    return render(request, 'clinico/nuevo_registro.html')


@login_required(login_url='usuarios:login')
def editar_registro(request, pk):
    """Edita un registro clínico existente, precargando los valores guardados."""
    if request.user.rol == 'administrador':
        messages.warning(request, 'Los administradores no tienen permiso para editar registros clínicos.')
        return redirect('usuarios:dashboard')

    registro = get_object_or_404(DatosClinico, pk=pk, paciente=request.user)

    if request.method == 'POST':
        try:
            _poblar_datos(registro, request.POST)
            registro.full_clean()
            registro.save()
            # Regenerar alertas (eliminar las anteriores de este registro)
            Alerta.objects.filter(datos_clinicos=registro).delete()
            _crear_alertas_clinicas(request.user, registro)
            messages.success(request, 'Registro actualizado correctamente.')
            return redirect('clinico:detalle', pk=registro.pk)
        except Exception as e:
            _manejar_error_validacion(request, e)

    return render(request, 'clinico/nuevo_registro.html', {'registro': registro})


# ── helpers privados ────────────────────────────────────────────────────────

def _crear_alertas_clinicas(usuario, datos):
    from prediccion.service import generar_alertas
    for a in generar_alertas(datos, {}):
        Alerta.objects.create(
            paciente=usuario,
            tipo=a['tipo'], severidad=a['severidad'],
            mensaje=a['mensaje'], datos_clinicos=datos,
        )


def _manejar_error_validacion(request, exc):
    from django.core.exceptions import ValidationError
    if isinstance(exc, ValidationError):
        msgs = '; '.join(
            f"{f}: {', '.join(errs)}" for f, errs in exc.message_dict.items()
        ) if hasattr(exc, 'message_dict') else str(exc)
        messages.error(request, f'Datos fuera de rango: {msgs}')
    else:
        messages.error(request, f'Error en los datos ingresados: {exc}')


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
