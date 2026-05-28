from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Prediccion
from clinico.models import DatosClinico
from alertas.models import Alerta
from .service import predecir_riesgo, generar_alertas, estimar_tiempo_enfermedad, adjust_family_risk


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
    """Muestra los resultados de una predicción, incluyendo estimación temporal."""
    prediccion = get_object_or_404(Prediccion, pk=pk, paciente=request.user)
    alertas = Alerta.objects.filter(datos_clinicos=prediccion.datos_clinicos)

    # ── Calcular tendencia por enfermedad ──────────────────────────────────
    pred_anterior = (
        Prediccion.objects
        .filter(paciente=request.user)
        .exclude(pk=prediccion.pk)
        .order_by('-fecha_prediccion')
        .first()
    )

    def _tendencia(campo):
        if not pred_anterior:
            return 'estable'
        actual = float(getattr(prediccion, campo))
        previo = float(getattr(pred_anterior, campo))
        if actual - previo > 5:  return 'subiendo'
        if previo - actual > 5:  return 'bajando'
        return 'estable'

    enfermedades = [
        {
            'nombre': 'Diabetes Tipo 2',
            'icono': 'bi-droplet',
            'color': '#e67e22',
            'riesgo': float(prediccion.riesgo_diabetes),
            'nivel': prediccion.nivel_diabetes,
            'descripcion': 'Basado en glucosa, IMC, edad y actividad física.',
            'tiempo': estimar_tiempo_enfermedad(prediccion.riesgo_diabetes, _tendencia('riesgo_diabetes')),
        },
        {
            'nombre': 'Hipertensión Arterial',
            'icono': 'bi-heart-pulse',
            'color': '#e74c3c',
            'riesgo': float(prediccion.riesgo_hipertension),
            'nivel': prediccion.nivel_hipertension,
            'descripcion': 'Basado en presión arterial, IMC, colesterol y tabaquismo.',
            'tiempo': estimar_tiempo_enfermedad(prediccion.riesgo_hipertension, _tendencia('riesgo_hipertension')),
        },
        {
            'nombre': 'Enfermedad Renal Crónica',
            'icono': 'bi-activity',
            'color': '#9b59b6',
            'riesgo': float(prediccion.riesgo_renal),
            'nivel': prediccion.nivel_renal,
            'descripcion': 'Basado en creatinina, presión arterial y glucosa.',
            'tiempo': estimar_tiempo_enfermedad(prediccion.riesgo_renal, _tendencia('riesgo_renal')),
        },
        {
            'nombre': 'Hígado Graso (NAFLD)',
            'icono': 'bi-shield',
            'color': '#27ae60',
            'riesgo': float(prediccion.riesgo_nafld),
            'nivel': prediccion.nivel_nafld,
            'descripcion': 'Basado en IMC, triglicéridos, glucosa y consumo de alcohol.',
            'tiempo': estimar_tiempo_enfermedad(prediccion.riesgo_nafld, _tendencia('riesgo_nafld')),
        },
        {
            'nombre': 'Insuficiencia Cardíaca',
            'icono': 'bi-heart',
            'color': '#c0392b',
            'riesgo': float(prediccion.riesgo_cardiaco),
            'nivel': prediccion.nivel_cardiaco,
            'descripcion': 'Basado en colesterol, tabaquismo, edad y riesgos acumulados.',
            'tiempo': estimar_tiempo_enfermedad(prediccion.riesgo_cardiaco, _tendencia('riesgo_cardiaco')),
        },
    ]

    return render(request, 'prediccion/resultado.html', {
        'prediccion': prediccion,
        'enfermedades': enfermedades,
        'alertas': alertas,
        'tiene_historial': pred_anterior is not None,
    })


@login_required(login_url='usuarios:login')
def historial_predicciones(request):
    """Lista de todas las predicciones del paciente."""
    predicciones = Prediccion.objects.filter(paciente=request.user)
    return render(request, 'prediccion/historial.html', {
        'predicciones': predicciones,
    })


# ═══════════════════════════════════════════════════════════════════════════
# API REST — Análisis con antecedentes familiares
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_analizar(request):
    """
    Ejecuta el modelo predictivo sobre un registro clínico existente,
    aplica el ajuste por antecedentes familiares y persiste la predicción.

    Autenticación: Bearer <JWT>  o  Cookie de sesión Django.
    Solo el propietario del registro puede analizarlo.

    Body JSON:
    {
        "datos_pk": 42,
        "antecedentes": {
            "diabetes_uno":       false,
            "diabetes_ambos":     false,
            "hipertension_uno":   true,
            "hipertension_ambos": false,
            "renal":              false,
            "nafld":              false,
            "cardiaco":           false
        }
    }

    Respuesta 201:
    {
        "prediccion_pk": 18,
        "riesgo_diabetes":     5.2,
        "nivel_diabetes":      "bajo",
        "riesgo_hipertension": 12.4,
        "nivel_hipertension":  "bajo",
        "riesgo_renal":        3.1,
        "nivel_renal":         "bajo",
        "riesgo_nafld":        42.7,
        "nivel_nafld":         "medio",
        "riesgo_cardiaco":     1.8,
        "nivel_cardiaco":      "bajo",
        "modelo_version":      "ml_v2_calibrado_af",
        "antecedentes_aplicados": true
    }
    """
    datos_pk     = request.data.get('datos_pk')
    antecedentes = request.data.get('antecedentes', {})

    # ── Validar entrada ───────────────────────────────────────────────────────
    if not datos_pk:
        return Response({'error': 'El campo datos_pk es obligatorio.'},
                        status=status.HTTP_400_BAD_REQUEST)

    # Solo el propietario puede analizar su propio registro
    datos = DatosClinico.objects.filter(
        pk=datos_pk, paciente=request.user
    ).first()
    if not datos:
        return Response({'error': 'Registro clínico no encontrado o sin permisos.'},
                        status=status.HTTP_404_NOT_FOUND)

    # ── Predicción base (ML o reglas) ─────────────────────────────────────────
    resultado_base = predecir_riesgo(datos)

    # ── Ajuste por antecedentes familiares ────────────────────────────────────
    tiene_antecedentes = any(antecedentes.values())
    if tiene_antecedentes:
        scores_base = {
            'diabetes':     float(resultado_base.get('riesgo_diabetes',     0)) / 100,
            'hipertension': float(resultado_base.get('riesgo_hipertension', 0)) / 100,
            'renal':        float(resultado_base.get('riesgo_renal',        0)) / 100,
            'nafld':        float(resultado_base.get('riesgo_nafld',        0)) / 100,
            'cardiaco':     float(resultado_base.get('riesgo_cardiaco',     0)) / 100,
        }
        ctx = {
            'imc':                float(datos.imc or 0),
            'riesgo_diabetes':    scores_base['diabetes'],
            'riesgo_hipertension': scores_base['hipertension'],
        }
        ajustados = adjust_family_risk(scores_base, antecedentes, ctx)
        from .service import _nivel_from_prob
        for key_score, rk, nk in [
            ('diabetes',     'riesgo_diabetes',     'nivel_diabetes'),
            ('hipertension', 'riesgo_hipertension', 'nivel_hipertension'),
            ('renal',        'riesgo_renal',        'nivel_renal'),
            ('nafld',        'riesgo_nafld',        'nivel_nafld'),
            ('cardiaco',     'riesgo_cardiaco',     'nivel_cardiaco'),
        ]:
            pct = round(ajustados[key_score] * 100, 2)
            resultado_base[rk] = pct
            resultado_base[nk] = _nivel_from_prob(pct)
        resultado_base['modelo_version'] = (
            resultado_base.get('modelo_version', 'ml_v2') + '_af'
        )

    # ── Persistir predicción ──────────────────────────────────────────────────
    existente = Prediccion.objects.filter(datos_clinicos=datos).first()
    if existente:
        # Actualizar si ya existe para este registro
        for field, val in resultado_base.items():
            if hasattr(existente, field):
                setattr(existente, field, val)
        existente.save()
        prediccion = existente
    else:
        prediccion = Prediccion.objects.create(
            paciente=request.user,
            datos_clinicos=datos,
            **resultado_base
        )

    # ── Generar alertas ───────────────────────────────────────────────────────
    for a in generar_alertas(datos, resultado_base):
        Alerta.objects.get_or_create(
            paciente=request.user,
            datos_clinicos=datos,
            tipo=a['tipo'],
            defaults={'severidad': a['severidad'], 'mensaje': a['mensaje']}
        )

    return Response({
        'prediccion_pk':          prediccion.pk,
        'riesgo_diabetes':        float(prediccion.riesgo_diabetes),
        'nivel_diabetes':         prediccion.nivel_diabetes,
        'riesgo_hipertension':    float(prediccion.riesgo_hipertension),
        'nivel_hipertension':     prediccion.nivel_hipertension,
        'riesgo_renal':           float(prediccion.riesgo_renal),
        'nivel_renal':            prediccion.nivel_renal,
        'riesgo_nafld':           float(prediccion.riesgo_nafld),
        'nivel_nafld':            prediccion.nivel_nafld,
        'riesgo_cardiaco':        float(prediccion.riesgo_cardiaco),
        'nivel_cardiaco':         prediccion.nivel_cardiaco,
        'modelo_version':         prediccion.modelo_version,
        'antecedentes_aplicados': tiene_antecedentes,
    }, status=status.HTTP_201_CREATED)
