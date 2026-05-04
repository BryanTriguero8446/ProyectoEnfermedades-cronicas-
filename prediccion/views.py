from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Prediccion
from clinico.models import DatosClinico
from alertas.models import Alerta
from .service import predecir_riesgo, generar_alertas


@login_required(login_url='usuarios:login')
def nueva_prediccion(request, datos_pk):
    """Genera una predicción a partir de un registro clínico."""
    datos = get_object_or_404(DatosClinico, pk=datos_pk, paciente=request.user)

    # Evitar duplicados: si ya existe predicción para estos datos, redirigir
    existente = Prediccion.objects.filter(datos_clinicos=datos).first()
    if existente:
        return redirect('prediccion:resultado', pk=existente.pk)

    resultado = predecir_riesgo(datos)

    prediccion = Prediccion.objects.create(
        paciente=request.user,
        datos_clinicos=datos,
        **resultado
    )

    # Alertas de predicción
    alertas_data = generar_alertas(datos, resultado)
    for a in alertas_data:
        if not Alerta.objects.filter(
            paciente=request.user,
            datos_clinicos=datos,
            tipo=a['tipo']
        ).exists():
            Alerta.objects.create(
                paciente=request.user,
                tipo=a['tipo'],
                severidad=a['severidad'],
                mensaje=a['mensaje'],
                datos_clinicos=datos,
            )

    messages.success(request, 'Análisis de riesgo completado.')
    return redirect('prediccion:resultado', pk=prediccion.pk)


@login_required(login_url='usuarios:login')
def resultado(request, pk):
    """Muestra los resultados de una predicción."""
    prediccion = get_object_or_404(Prediccion, pk=pk, paciente=request.user)
    alertas = Alerta.objects.filter(datos_clinicos=prediccion.datos_clinicos)

    enfermedades = [
        {
            'nombre': 'Diabetes Tipo 2',
            'icono': 'bi-droplet',
            'color': '#e67e22',
            'riesgo': float(prediccion.riesgo_diabetes),
            'nivel': prediccion.nivel_diabetes,
            'descripcion': 'Basado en glucosa, IMC, edad y actividad física.',
        },
        {
            'nombre': 'Hipertensión Arterial',
            'icono': 'bi-heart-pulse',
            'color': '#e74c3c',
            'riesgo': float(prediccion.riesgo_hipertension),
            'nivel': prediccion.nivel_hipertension,
            'descripcion': 'Basado en presión arterial, IMC, colesterol y tabaquismo.',
        },
        {
            'nombre': 'Enfermedad Renal Crónica',
            'icono': 'bi-activity',
            'color': '#9b59b6',
            'riesgo': float(prediccion.riesgo_renal),
            'nivel': prediccion.nivel_renal,
            'descripcion': 'Basado en creatinina, presión arterial y glucosa.',
        },
        {
            'nombre': 'Hígado Graso (NAFLD)',
            'icono': 'bi-shield',
            'color': '#27ae60',
            'riesgo': float(prediccion.riesgo_nafld),
            'nivel': prediccion.nivel_nafld,
            'descripcion': 'Basado en IMC, triglicéridos, glucosa y consumo de alcohol.',
        },
        {
            'nombre': 'Insuficiencia Cardíaca',
            'icono': 'bi-heart',
            'color': '#c0392b',
            'riesgo': float(prediccion.riesgo_cardiaco),
            'nivel': prediccion.nivel_cardiaco,
            'descripcion': 'Basado en colesterol, tabaquismo, edad y riesgos acumulados.',
        },
    ]

    return render(request, 'prediccion/resultado.html', {
        'prediccion': prediccion,
        'enfermedades': enfermedades,
        'alertas': alertas,
    })


@login_required(login_url='usuarios:login')
def historial_predicciones(request):
    """Lista de todas las predicciones del paciente."""
    predicciones = Prediccion.objects.filter(paciente=request.user)
    return render(request, 'prediccion/historial.html', {
        'predicciones': predicciones,
    })
