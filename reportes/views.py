import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from .models import Reporte
from clinico.models import DatosClinico
from prediccion.models import Prediccion


@login_required(login_url='usuarios:login')
def lista_reportes(request):
    reportes = Reporte.objects.filter(paciente=request.user)
    return render(request, 'reportes/lista.html', {'reportes': reportes})


@login_required(login_url='usuarios:login')
def generar_csv(request):
    """Genera reporte CSV con historial clínico completo."""
    registros = DatosClinico.objects.filter(paciente=request.user)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    fname = f"clinicallens_historial_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    response.write('﻿')  # BOM para Excel

    writer = csv.writer(response)
    writer.writerow([
        'Fecha', 'Edad', 'Peso (kg)', 'Altura (m)', 'IMC',
        'Presión Sistólica', 'Presión Diastólica',
        'Glucosa (mg/dL)', 'Frecuencia Cardíaca',
        'Colesterol', 'Triglicéridos', 'Creatinina',
        'Actividad Física', 'Fumador', 'Alcohol', 'Observaciones'
    ])

    for r in registros:
        writer.writerow([
            r.fecha_registro.strftime('%d/%m/%Y %H:%M'),
            r.edad, r.peso, r.altura, r.imc,
            r.presion_sistolica, r.presion_diastolica,
            r.glucosa, r.frecuencia_cardiaca,
            r.colesterol or '', r.trigliceridos or '', r.creatinina or '',
            r.get_actividad_fisica_display(),
            'Sí' if r.fumador else 'No',
            'Sí' if r.alcohol else 'No',
            r.observaciones,
        ])

    Reporte.objects.create(
        paciente=request.user,
        formato='csv',
        tipo='clinico',
        estado='listo',
        generado_por=request.user,
        parametros={'registros': registros.count()},
    )

    return response


@login_required(login_url='usuarios:login')
def generar_csv_predicciones(request):
    """Genera reporte CSV con historial de predicciones."""
    predicciones = Prediccion.objects.filter(paciente=request.user)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    fname = f"clinicallens_predicciones_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    response.write('﻿')

    writer = csv.writer(response)
    writer.writerow([
        'Fecha', 'Versión Modelo',
        '% Diabetes', 'Nivel Diabetes',
        '% Hipertensión', 'Nivel Hipertensión',
        '% Renal', 'Nivel Renal',
        '% NAFLD', 'Nivel NAFLD',
        '% Cardíaco', 'Nivel Cardíaco',
        'Nivel General',
    ])

    for p in predicciones:
        writer.writerow([
            p.fecha_prediccion.strftime('%d/%m/%Y %H:%M'),
            p.modelo_version,
            p.riesgo_diabetes, p.nivel_diabetes,
            p.riesgo_hipertension, p.nivel_hipertension,
            p.riesgo_renal, p.nivel_renal,
            p.riesgo_nafld, p.nivel_nafld,
            p.riesgo_cardiaco, p.nivel_cardiaco,
            p.nivel_general,
        ])

    Reporte.objects.create(
        paciente=request.user,
        formato='csv',
        tipo='prediccion',
        estado='listo',
        generado_por=request.user,
        parametros={'predicciones': predicciones.count()},
    )

    return response
