"""
Servicio de predicción de riesgo de enfermedades crónicas.

Este módulo implementa un sistema de reglas clínicas como placeholder.
Cuando los modelos ML (.pkl) estén entrenados, reemplazar el método
_predict_with_rules() por _predict_with_model() en cada enfermedad.
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent / 'ml_models'


def _nivel(prob: float) -> str:
    if prob >= 65:
        return 'alto'
    elif prob >= 35:
        return 'medio'
    return 'bajo'


def _clamp(val: float, lo: float = 0.0, hi: float = 99.9) -> float:
    return max(lo, min(hi, val))


def predecir_riesgo(datos) -> dict:
    """
    Calcula el riesgo para las 5 enfermedades crónicas.

    Parámetros (datos: DatosClinico instance):
        edad, peso, altura, imc, presion_sistolica, presion_diastolica,
        glucosa, frecuencia_cardiaca, colesterol, trigliceridos, creatinina,
        actividad_fisica, fumador, alcohol

    Retorna dict con probabilidades y niveles para cada enfermedad.
    """
    edad = datos.edad or 0
    imc = float(datos.imc or 0)
    glucosa = float(datos.glucosa or 0)
    p_sis = datos.presion_sistolica or 0
    p_dia = datos.presion_diastolica or 0
    fc = datos.frecuencia_cardiaca or 0
    colesterol = float(datos.colesterol or 180)
    trigliceridos = float(datos.trigliceridos or 150)
    creatinina = float(datos.creatinina or 1.0)
    fumador = datos.fumador
    alcohol = datos.alcohol
    actividad = datos.actividad_fisica

    factor_actividad = {
        'sedentario': 1.3, 'leve': 1.1, 'moderado': 1.0, 'activo': 0.85, 'muy_activo': 0.7
    }.get(actividad, 1.0)

    # ─── DIABETES TIPO 2 ─────────────────────────────────────────────
    d_score = 0.0
    if glucosa >= 126:
        d_score += 45
    elif glucosa >= 100:
        d_score += 25
    elif glucosa >= 90:
        d_score += 10

    if imc >= 30:
        d_score += 20
    elif imc >= 25:
        d_score += 12

    if edad >= 55:
        d_score += 15
    elif edad >= 45:
        d_score += 8
    elif edad >= 35:
        d_score += 4

    if trigliceridos >= 200:
        d_score += 8
    if fumador:
        d_score += 5
    if alcohol:
        d_score += 3

    d_score *= factor_actividad
    riesgo_diabetes = _clamp(d_score)

    # ─── HIPERTENSIÓN ARTERIAL ────────────────────────────────────────
    h_score = 0.0
    if p_sis >= 140 or p_dia >= 90:
        h_score += 50
    elif p_sis >= 130 or p_dia >= 80:
        h_score += 30
    elif p_sis >= 120:
        h_score += 15

    if imc >= 30:
        h_score += 15
    elif imc >= 25:
        h_score += 8

    if edad >= 60:
        h_score += 12
    elif edad >= 45:
        h_score += 7

    if colesterol >= 240:
        h_score += 8
    elif colesterol >= 200:
        h_score += 4

    if fumador:
        h_score += 8
    if alcohol:
        h_score += 6

    h_score *= factor_actividad
    riesgo_hipertension = _clamp(h_score)

    # ─── ENFERMEDAD RENAL CRÓNICA ─────────────────────────────────────
    r_score = 0.0
    if creatinina >= 2.0:
        r_score += 45
    elif creatinina >= 1.5:
        r_score += 25
    elif creatinina >= 1.2:
        r_score += 10

    # Diabetes e hipertensión son factores de riesgo para ERC
    r_score += riesgo_diabetes * 0.3
    r_score += riesgo_hipertension * 0.2

    if edad >= 60:
        r_score += 10
    if imc >= 30:
        r_score += 5

    riesgo_renal = _clamp(r_score)

    # ─── HÍGADO GRASO NO ALCOHÓLICO (NAFLD) ──────────────────────────
    n_score = 0.0
    if imc >= 35:
        n_score += 40
    elif imc >= 30:
        n_score += 25
    elif imc >= 25:
        n_score += 12

    if trigliceridos >= 200:
        n_score += 20
    elif trigliceridos >= 150:
        n_score += 10

    if glucosa >= 126:
        n_score += 15
    elif glucosa >= 100:
        n_score += 8

    if alcohol:
        n_score += 15
    if colesterol >= 240:
        n_score += 8

    n_score *= factor_actividad
    riesgo_nafld = _clamp(n_score)

    # ─── INSUFICIENCIA CARDÍACA ───────────────────────────────────────
    c_score = 0.0
    if fc > 100 or fc < 50:
        c_score += 15

    # Acumula riesgo cardiovascular de las otras enfermedades
    c_score += riesgo_hipertension * 0.3
    c_score += riesgo_diabetes * 0.2
    c_score += riesgo_renal * 0.15

    if colesterol >= 240:
        c_score += 15
    elif colesterol >= 200:
        c_score += 8

    if fumador:
        c_score += 15
    if edad >= 65:
        c_score += 12
    elif edad >= 50:
        c_score += 7

    c_score *= factor_actividad
    riesgo_cardiaco = _clamp(c_score)

    return {
        'riesgo_diabetes': round(riesgo_diabetes, 2),
        'nivel_diabetes': _nivel(riesgo_diabetes),
        'riesgo_hipertension': round(riesgo_hipertension, 2),
        'nivel_hipertension': _nivel(riesgo_hipertension),
        'riesgo_renal': round(riesgo_renal, 2),
        'nivel_renal': _nivel(riesgo_renal),
        'riesgo_nafld': round(riesgo_nafld, 2),
        'nivel_nafld': _nivel(riesgo_nafld),
        'riesgo_cardiaco': round(riesgo_cardiaco, 2),
        'nivel_cardiaco': _nivel(riesgo_cardiaco),
        'modelo_version': 'rule_based_v1',
    }


def generar_alertas(datos, prediccion_data: dict) -> list:
    """Genera alertas automáticas a partir de datos clínicos y predicción."""
    alertas = []

    glucosa = float(datos.glucosa)
    if glucosa > 126:
        alertas.append({
            'tipo': 'glucosa_alta',
            'severidad': 'danger',
            'mensaje': f'Glucosa en ayunas elevada: {glucosa} mg/dL. '
                       f'Valor normal: menor a 100 mg/dL. Se recomienda consulta médica urgente.'
        })
    elif glucosa > 100:
        alertas.append({
            'tipo': 'glucosa_alta',
            'severidad': 'warning',
            'mensaje': f'Glucosa en prediabetes: {glucosa} mg/dL. '
                       f'Rango prediabetes: 100-125 mg/dL. Se recomienda revisión médica.'
        })
    elif glucosa < 70:
        alertas.append({
            'tipo': 'glucosa_baja',
            'severidad': 'danger',
            'mensaje': f'Glucosa baja (hipoglucemia): {glucosa} mg/dL. '
                       f'Se recomienda atención médica inmediata.'
        })

    s, d = datos.presion_sistolica, datos.presion_diastolica
    if s >= 140 or d >= 90:
        alertas.append({
            'tipo': 'presion_alta',
            'severidad': 'danger',
            'mensaje': f'Hipertensión arterial detectada: {s}/{d} mmHg. '
                       f'Consulte a su médico.'
        })
    elif s >= 130 or d >= 80:
        alertas.append({
            'tipo': 'presion_alta',
            'severidad': 'warning',
            'mensaje': f'Presión arterial elevada: {s}/{d} mmHg. '
                       f'Se recomienda seguimiento.'
        })

    imc = float(datos.imc or 0)
    if imc >= 30:
        alertas.append({
            'tipo': 'imc_alto',
            'severidad': 'warning',
            'mensaje': f'IMC indica obesidad: {imc:.1f} kg/m². '
                       f'Se recomienda consulta nutricional.'
        })
    elif imc < 18.5 and imc > 0:
        alertas.append({
            'tipo': 'imc_bajo',
            'severidad': 'warning',
            'mensaje': f'IMC indica bajo peso: {imc:.1f} kg/m². '
                       f'Se recomienda evaluación nutricional.'
        })

    fc = datos.frecuencia_cardiaca
    if fc > 100:
        alertas.append({
            'tipo': 'frecuencia_anormal',
            'severidad': 'warning',
            'mensaje': f'Frecuencia cardíaca elevada (taquicardia): {fc} lpm. '
                       f'Rango normal: 60-100 lpm.'
        })
    elif fc < 60:
        alertas.append({
            'tipo': 'frecuencia_anormal',
            'severidad': 'info',
            'mensaje': f'Frecuencia cardíaca baja (bradicardia): {fc} lpm. '
                       f'Consulte si presenta síntomas.'
        })

    enfermedades = {
        'diabetes': ('riesgo_alto_diabetes', 'Diabetes Tipo 2', prediccion_data.get('riesgo_diabetes', 0)),
        'hipertension': ('riesgo_alto_hipertension', 'Hipertensión', prediccion_data.get('riesgo_hipertension', 0)),
        'renal': ('riesgo_alto_renal', 'Enfermedad Renal Crónica', prediccion_data.get('riesgo_renal', 0)),
        'nafld': ('riesgo_alto_nafld', 'Hígado Graso', prediccion_data.get('riesgo_nafld', 0)),
        'cardiaco': ('riesgo_alto_cardiaco', 'Insuficiencia Cardíaca', prediccion_data.get('riesgo_cardiaco', 0)),
    }
    for key, (tipo, nombre, riesgo) in enfermedades.items():
        nivel = prediccion_data.get(f'nivel_{key}', 'bajo')
        if nivel == 'alto':
            alertas.append({
                'tipo': tipo,
                'severidad': 'danger',
                'mensaje': f'Riesgo ALTO de {nombre}: {riesgo:.1f}%. '
                           f'Se recomienda consulta médica a la brevedad.'
            })

    return alertas
