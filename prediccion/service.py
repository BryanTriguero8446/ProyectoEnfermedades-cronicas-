"""
Servicio de prediccion de riesgo de enfermedades cronicas.

Modo de operacion:
  - Si los modelos .pkl estan disponibles -> usa Machine Learning
  - Si no estan disponibles (fallo de carga) -> usa reglas clinicas (fallback)

Los modelos .pkl viven en prediccion/ml_models/ y fueron generados
por train_models.py a partir de los datasets en ml_datasets/.
"""
import logging
import joblib
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent / 'ml_models'

# Features que los modelos esperan (en este orden exacto)
FEATURES = ["age", "bmi", "glucose", "systolic_bp", "diastolic_bp", "cholesterol"]

ENFERMEDADES = ['diabetes', 'hipertension', 'renal', 'higado_graso', 'insuficiencia_cardiaca']

# Mapa interno: nombres usados por el modelo de Django -> nombres del ML
DJANGO_TO_INTERNAL = {
    'diabetes': 'diabetes',
    'hipertension': 'hipertension',
    'renal': 'renal',
    'nafld': 'higado_graso',          # el frontend usa "nafld" pero el dataset es "higado_graso"
    'cardiaco': 'insuficiencia_cardiaca',
}

# Cache global de modelos cargados (se carga una sola vez)
_MODELOS_CACHE = {}
_MODELOS_DISPONIBLES = False


def _cargar_modelos():
    """Carga los modelos .pkl en memoria. Se llama una sola vez."""
    global _MODELOS_CACHE, _MODELOS_DISPONIBLES

    if _MODELOS_CACHE:
        return _MODELOS_DISPONIBLES

    try:
        for enf in ENFERMEDADES:
            f_disease = MODELS_DIR / f"{enf}_disease.pkl"
            f_risk    = MODELS_DIR / f"{enf}_risk.pkl"
            if not f_disease.exists() or not f_risk.exists():
                logger.warning(f"Modelo faltante para {enf}: {f_disease.name} o {f_risk.name}")
                _MODELOS_DISPONIBLES = False
                return False
            _MODELOS_CACHE[f"{enf}_disease"] = joblib.load(f_disease)
            _MODELOS_CACHE[f"{enf}_risk"]    = joblib.load(f_risk)

        _MODELOS_DISPONIBLES = True
        algos = {k: v['algo'] for k, v in _MODELOS_CACHE.items()}
        logger.info(f"Modelos ML cargados: {algos}")
        return True
    except Exception as e:
        logger.error(f"Error cargando modelos ML, usando reglas: {e}")
        _MODELOS_DISPONIBLES = False
        return False


def _nivel_str(val):
    """Convierte 0/1/2 a 'bajo'/'medio'/'alto'."""
    return {0: 'bajo', 1: 'medio', 2: 'alto'}.get(int(val), 'bajo')


def _nivel_from_prob(prob):
    """Convierte probabilidad % a nivel cuando no hay modelo de riesgo."""
    if prob >= 65:  return 'alto'
    if prob >= 35:  return 'medio'
    return 'bajo'


def _clamp(val, lo=0.0, hi=99.9):
    return max(lo, min(hi, val))


def _extraer_features(datos):
    """Construye el vector de features en el orden exacto que el modelo espera."""
    edad = datos.edad or 0
    imc  = float(datos.imc or 0)
    glu  = float(datos.glucosa or 0)
    sis  = datos.presion_sistolica or 0
    dia  = datos.presion_diastolica or 0
    col  = float(datos.colesterol or 195)   # default si esta vacio: promedio adulto

    return np.array([[edad, imc, glu, sis, dia, col]])


# ═════════════════════════════════════════════════════════════════════════════
# PREDICCION CON MACHINE LEARNING
# ═════════════════════════════════════════════════════════════════════════════

def _predecir_con_ml(datos):
    """Usa los modelos .pkl entrenados para predecir."""
    X = _extraer_features(datos)
    resultados = {}

    for django_key, internal_key in DJANGO_TO_INTERNAL.items():
        modelo_disease = _MODELOS_CACHE[f"{internal_key}_disease"]['model']
        modelo_risk    = _MODELOS_CACHE[f"{internal_key}_risk"]['model']

        # Probabilidad de tener la enfermedad (clase 1)
        prob = modelo_disease.predict_proba(X)[0]
        if len(prob) > 1:
            riesgo_pct = float(prob[1]) * 100
        else:
            riesgo_pct = float(prob[0]) * 100
        riesgo_pct = _clamp(riesgo_pct)

        # Nivel de riesgo (0/1/2) usando el modelo de risk_level
        nivel_num = modelo_risk.predict(X)[0]
        nivel_str = _nivel_str(nivel_num)

        resultados[f'riesgo_{django_key}'] = round(riesgo_pct, 2)
        resultados[f'nivel_{django_key}']  = nivel_str

    resultados['modelo_version'] = 'ml_v1_rf_gb'
    return resultados


# ═════════════════════════════════════════════════════════════════════════════
# PREDICCION CON REGLAS CLINICAS (FALLBACK)
# ═════════════════════════════════════════════════════════════════════════════

def _predecir_con_reglas(datos):
    """Sistema de reglas clinicas usado como respaldo si los .pkl fallan."""
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

    # Diabetes
    d_score = 0.0
    if glucosa >= 126: d_score += 45
    elif glucosa >= 100: d_score += 25
    elif glucosa >= 90: d_score += 10
    if imc >= 30: d_score += 20
    elif imc >= 25: d_score += 12
    if edad >= 55: d_score += 15
    elif edad >= 45: d_score += 8
    elif edad >= 35: d_score += 4
    if trigliceridos >= 200: d_score += 8
    if fumador: d_score += 5
    if alcohol: d_score += 3
    d_score *= factor_actividad
    riesgo_diabetes = _clamp(d_score)

    # Hipertension
    h_score = 0.0
    if p_sis >= 140 or p_dia >= 90: h_score += 50
    elif p_sis >= 130 or p_dia >= 80: h_score += 30
    elif p_sis >= 120: h_score += 15
    if imc >= 30: h_score += 15
    elif imc >= 25: h_score += 8
    if edad >= 60: h_score += 12
    elif edad >= 45: h_score += 7
    if colesterol >= 240: h_score += 8
    elif colesterol >= 200: h_score += 4
    if fumador: h_score += 8
    if alcohol: h_score += 6
    h_score *= factor_actividad
    riesgo_hipertension = _clamp(h_score)

    # Renal
    r_score = 0.0
    if creatinina >= 2.0: r_score += 45
    elif creatinina >= 1.5: r_score += 25
    elif creatinina >= 1.2: r_score += 10
    r_score += riesgo_diabetes * 0.3
    r_score += riesgo_hipertension * 0.2
    if edad >= 60: r_score += 10
    if imc >= 30: r_score += 5
    riesgo_renal = _clamp(r_score)

    # NAFLD
    n_score = 0.0
    if imc >= 35: n_score += 40
    elif imc >= 30: n_score += 25
    elif imc >= 25: n_score += 12
    if trigliceridos >= 200: n_score += 20
    elif trigliceridos >= 150: n_score += 10
    if glucosa >= 126: n_score += 15
    elif glucosa >= 100: n_score += 8
    if alcohol: n_score += 15
    if colesterol >= 240: n_score += 8
    n_score *= factor_actividad
    riesgo_nafld = _clamp(n_score)

    # Cardiaco
    c_score = 0.0
    if fc > 100 or fc < 60: c_score += 15
    c_score += riesgo_hipertension * 0.3
    c_score += riesgo_diabetes * 0.2
    c_score += riesgo_renal * 0.15
    if colesterol >= 240: c_score += 15
    elif colesterol >= 200: c_score += 8
    if fumador: c_score += 15
    if edad >= 65: c_score += 12
    elif edad >= 50: c_score += 7
    c_score *= factor_actividad
    riesgo_cardiaco = _clamp(c_score)

    return {
        'riesgo_diabetes': round(riesgo_diabetes, 2),
        'nivel_diabetes': _nivel_from_prob(riesgo_diabetes),
        'riesgo_hipertension': round(riesgo_hipertension, 2),
        'nivel_hipertension': _nivel_from_prob(riesgo_hipertension),
        'riesgo_renal': round(riesgo_renal, 2),
        'nivel_renal': _nivel_from_prob(riesgo_renal),
        'riesgo_nafld': round(riesgo_nafld, 2),
        'nivel_nafld': _nivel_from_prob(riesgo_nafld),
        'riesgo_cardiaco': round(riesgo_cardiaco, 2),
        'nivel_cardiaco': _nivel_from_prob(riesgo_cardiaco),
        'modelo_version': 'rule_based_v1',
    }


# ═════════════════════════════════════════════════════════════════════════════
# API PUBLICA
# ═════════════════════════════════════════════════════════════════════════════

def predecir_riesgo(datos):
    """
    Calcula el riesgo para las 5 enfermedades cronicas.

    Usa modelos ML si estan disponibles, sino aplica reglas clinicas.
    Retorna dict con probabilidades y niveles para cada enfermedad.
    """
    if _cargar_modelos():
        try:
            return _predecir_con_ml(datos)
        except Exception as e:
            logger.error(f"Fallo prediccion ML, usando reglas: {e}")

    return _predecir_con_reglas(datos)


# ═════════════════════════════════════════════════════════════════════════════
# ALERTAS (independiente del modelo, basado en valores clinicos directos)
# ═════════════════════════════════════════════════════════════════════════════

def generar_alertas(datos, prediccion_data):
    """Genera alertas automaticas a partir de datos clinicos y prediccion."""
    alertas = []

    glucosa = float(datos.glucosa)
    if glucosa > 126:
        alertas.append({
            'tipo': 'glucosa_alta', 'severidad': 'danger',
            'mensaje': f'Glucosa en ayunas elevada: {glucosa} mg/dL. '
                       f'Valor normal: menor a 100 mg/dL. Se recomienda consulta medica urgente.'
        })
    elif glucosa > 100:
        alertas.append({
            'tipo': 'glucosa_alta', 'severidad': 'warning',
            'mensaje': f'Glucosa en prediabetes: {glucosa} mg/dL. '
                       f'Rango prediabetes: 100-125 mg/dL. Se recomienda revision medica.'
        })
    elif glucosa < 70:
        alertas.append({
            'tipo': 'glucosa_baja', 'severidad': 'danger',
            'mensaje': f'Glucosa baja (hipoglucemia): {glucosa} mg/dL. '
                       f'Se recomienda atencion medica inmediata.'
        })

    s, d = datos.presion_sistolica, datos.presion_diastolica
    if s >= 140 or d >= 90:
        alertas.append({
            'tipo': 'presion_alta', 'severidad': 'danger',
            'mensaje': f'Hipertension arterial detectada: {s}/{d} mmHg. Consulte a su medico.'
        })
    elif s >= 130 or d >= 80:
        alertas.append({
            'tipo': 'presion_alta', 'severidad': 'warning',
            'mensaje': f'Presion arterial elevada: {s}/{d} mmHg. Se recomienda seguimiento.'
        })

    imc = float(datos.imc or 0)
    if imc >= 30:
        alertas.append({
            'tipo': 'imc_alto', 'severidad': 'warning',
            'mensaje': f'IMC indica obesidad: {imc:.1f} kg/m2. Se recomienda consulta nutricional.'
        })
    elif imc < 18.5 and imc > 0:
        alertas.append({
            'tipo': 'imc_bajo', 'severidad': 'warning',
            'mensaje': f'IMC indica bajo peso: {imc:.1f} kg/m2. Se recomienda evaluacion nutricional.'
        })

    fc = datos.frecuencia_cardiaca
    if fc > 100:
        alertas.append({
            'tipo': 'frecuencia_anormal', 'severidad': 'warning',
            'mensaje': f'Frecuencia cardiaca elevada (taquicardia): {fc} lpm. Rango normal: 60-100 lpm.'
        })
    elif fc < 60:
        alertas.append({
            'tipo': 'frecuencia_anormal', 'severidad': 'info',
            'mensaje': f'Frecuencia cardiaca baja (bradicardia): {fc} lpm. Consulte si presenta sintomas.'
        })

    enfermedades = {
        'diabetes': ('riesgo_alto_diabetes', 'Diabetes Tipo 2', prediccion_data.get('riesgo_diabetes', 0)),
        'hipertension': ('riesgo_alto_hipertension', 'Hipertension', prediccion_data.get('riesgo_hipertension', 0)),
        'renal': ('riesgo_alto_renal', 'Enfermedad Renal Cronica', prediccion_data.get('riesgo_renal', 0)),
        'nafld': ('riesgo_alto_nafld', 'Higado Graso', prediccion_data.get('riesgo_nafld', 0)),
        'cardiaco': ('riesgo_alto_cardiaco', 'Insuficiencia Cardiaca', prediccion_data.get('riesgo_cardiaco', 0)),
    }
    for key, (tipo, nombre, riesgo) in enfermedades.items():
        nivel = prediccion_data.get(f'nivel_{key}', 'bajo')
        if nivel == 'alto':
            alertas.append({
                'tipo': tipo, 'severidad': 'danger',
                'mensaje': f'Riesgo ALTO de {nombre}: {riesgo:.1f}%. Se recomienda consulta medica a la brevedad.'
            })

    return alertas
