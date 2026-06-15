import json
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from usuarios.models import Usuario
from clinico.models import DatosClinico
from prediccion.models import Prediccion
from prediccion import service


def crear_usuario(correo='pac@pred.com'):
    return Usuario.objects.create_user(
        correo=correo, nombre='María', apellido='Test', password='Pass1234!'
    )


def datos_clinicos(paciente, **kwargs):
    defaults = dict(
        paciente=paciente,
        edad=35, peso=70.0, altura=1.75,
        presion_sistolica=120, presion_diastolica=80,
        glucosa=90.0, frecuencia_cardiaca=72,
        actividad_fisica='moderado',
    )
    defaults.update(kwargs)
    d = DatosClinico(**defaults)
    d.save()
    return d


# ─────────────────────────────────────────────
# SERVICE – funciones auxiliares
# ─────────────────────────────────────────────
class ServiceHelperTest(TestCase):

    def test_nivel_str_0_es_bajo(self):
        self.assertEqual(service._nivel_str(0), 'bajo')

    def test_nivel_str_1_es_medio(self):
        self.assertEqual(service._nivel_str(1), 'medio')

    def test_nivel_str_2_es_alto(self):
        self.assertEqual(service._nivel_str(2), 'alto')

    def test_nivel_str_valor_desconocido_es_bajo(self):
        self.assertEqual(service._nivel_str(99), 'bajo')

    def test_nivel_from_prob_bajo(self):
        self.assertEqual(service._nivel_from_prob(30), 'bajo')

    def test_nivel_from_prob_medio(self):
        self.assertEqual(service._nivel_from_prob(50), 'medio')

    def test_nivel_from_prob_alto(self):
        self.assertEqual(service._nivel_from_prob(70), 'alto')

    def test_nivel_from_prob_limite_35_es_medio(self):
        self.assertEqual(service._nivel_from_prob(35), 'medio')

    def test_nivel_from_prob_limite_65_es_alto(self):
        self.assertEqual(service._nivel_from_prob(65), 'alto')

    def test_clamp_dentro_del_rango(self):
        self.assertEqual(service._clamp(50.0), 50.0)

    def test_clamp_valor_negativo(self):
        self.assertEqual(service._clamp(-10.0), 0.0)

    def test_clamp_valor_sobre_maximo(self):
        self.assertEqual(service._clamp(150.0), 99.9)

    def test_clamp_exactamente_99_9(self):
        self.assertEqual(service._clamp(99.9), 99.9)


# ─────────────────────────────────────────────
# SERVICE – reglas clínicas (fallback)
# ─────────────────────────────────────────────
class ReglasClinicasTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()

    def _predecir(self, **kwargs):
        d = datos_clinicos(self.paciente, **kwargs)
        # Forzar uso de reglas (sin modelos ML)
        with patch.object(service, '_MODELOS_CACHE', {}):
            with patch.object(service, '_MODELOS_DISPONIBLES', False):
                return service._predecir_con_reglas(d)

    def test_retorna_todas_las_claves(self):
        r = self._predecir()
        claves = ['riesgo_diabetes', 'nivel_diabetes', 'riesgo_hipertension',
                  'nivel_hipertension', 'riesgo_renal', 'nivel_renal',
                  'riesgo_nafld', 'nivel_nafld', 'riesgo_cardiaco',
                  'nivel_cardiaco', 'modelo_version']
        for c in claves:
            self.assertIn(c, r, msg=f"Falta clave '{c}' en resultado")

    def test_modelo_version_reglas(self):
        r = self._predecir()
        self.assertEqual(r['modelo_version'], 'rule_based_v1')

    def test_valores_dentro_de_0_a_100(self):
        r = self._predecir(glucosa=200, presion_sistolica=160, presion_diastolica=100)
        for campo in ('riesgo_diabetes', 'riesgo_hipertension',
                      'riesgo_renal', 'riesgo_nafld', 'riesgo_cardiaco'):
            self.assertGreaterEqual(r[campo], 0, msg=f"{campo} negativo")
            self.assertLessEqual(r[campo], 99.9, msg=f"{campo} supera 99.9")

    def test_paciente_sano_riesgos_bajos(self):
        # Valores completamente normales → todos deben ser bajo
        r = self._predecir(
            edad=25, peso=60.0, altura=1.70,
            glucosa=85.0, presion_sistolica=110, presion_diastolica=70,
            frecuencia_cardiaca=65, colesterol=160.0, trigliceridos=100.0,
            creatinina=0.9, actividad_fisica='activo',
        )
        self.assertEqual(r['nivel_diabetes'], 'bajo')
        self.assertEqual(r['nivel_hipertension'], 'bajo')

    def test_diabetico_riesgo_alto(self):
        r = self._predecir(
            edad=55, peso=100.0, altura=1.70,  # IMC≈34.6 (obesidad)
            glucosa=140.0,                     # diabetes evidente
            presion_sistolica=130, presion_diastolica=85,
        )
        self.assertGreater(r['riesgo_diabetes'], 50)

    def test_hipertenso_riesgo_alto(self):
        r = self._predecir(
            presion_sistolica=160, presion_diastolica=100,
            edad=60, peso=95.0, altura=1.70,
        )
        self.assertGreater(r['riesgo_hipertension'], 50)

    def test_obesidad_aumenta_nafld(self):
        r_normal = self._predecir(peso=65.0, altura=1.75)
        r_obeso = self._predecir(peso=120.0, altura=1.75)
        self.assertGreater(r_obeso['riesgo_nafld'], r_normal['riesgo_nafld'])

    def test_fumador_aumenta_riesgo_cardiaco(self):
        r_no = self._predecir(fumador=False)
        r_si = self._predecir(fumador=True)
        self.assertGreater(r_si['riesgo_cardiaco'], r_no['riesgo_cardiaco'])

    def test_actividad_intensa_reduce_riesgo(self):
        r_sed = self._predecir(actividad_fisica='sedentario')
        r_act = self._predecir(actividad_fisica='muy_activo')
        self.assertGreater(r_sed['riesgo_diabetes'], r_act['riesgo_diabetes'])

    def test_umbral_fc_alineado_en_60(self):
        """
        Verifica que el umbral de bradicardia sea consistente a 60 bpm
        tanto en _predecir_con_reglas() como en generar_alertas().
        """
        # fc=55 debe generar alerta de bradicardia (< 60)
        d = datos_clinicos(self.paciente, frecuencia_cardiaca=55)
        alertas = service.generar_alertas(d, {})
        tipos_alerta = [a['tipo'] for a in alertas]
        self.assertIn('frecuencia_anormal', tipos_alerta)

        # Y también debe sumar al score cardíaco en reglas (fc < 60)
        d_55 = datos_clinicos(self.paciente, frecuencia_cardiaca=55)
        d_72 = datos_clinicos(self.paciente, frecuencia_cardiaca=72)
        r55 = service._predecir_con_reglas(d_55)
        r72 = service._predecir_con_reglas(d_72)
        self.assertGreater(r55['riesgo_cardiaco'], r72['riesgo_cardiaco'],
                           "fc=55 debe tener mayor riesgo cardíaco que fc=72 (normal)")


# ─────────────────────────────────────────────
# MODELO Prediccion – propiedades
# ─────────────────────────────────────────────
class PrediccionModelTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()
        self.datos = datos_clinicos(self.paciente)

    def _make_pred(self, **kwargs):
        defaults = dict(
            paciente=self.paciente,
            datos_clinicos=self.datos,
            riesgo_diabetes=20, nivel_diabetes='bajo',
            riesgo_hipertension=15, nivel_hipertension='bajo',
            riesgo_renal=10, nivel_renal='bajo',
            riesgo_nafld=5, nivel_nafld='bajo',
            riesgo_cardiaco=8, nivel_cardiaco='bajo',
        )
        defaults.update(kwargs)
        return Prediccion(**defaults)

    def test_riesgo_maximo_devuelve_el_mayor(self):
        p = self._make_pred(riesgo_diabetes=75, nivel_diabetes='alto')
        pct, nombre = p.riesgo_maximo
        self.assertAlmostEqual(pct, 75.0)
        self.assertEqual(nombre, 'Diabetes')

    def test_riesgo_maximo_cuando_todos_cero(self):
        p = self._make_pred(
            riesgo_diabetes=0, riesgo_hipertension=0,
            riesgo_renal=0, riesgo_nafld=0, riesgo_cardiaco=0
        )
        pct, _ = p.riesgo_maximo
        self.assertEqual(pct, 0.0)

    def test_nivel_general_alto_si_alguno_es_alto(self):
        p = self._make_pred(nivel_renal='alto')
        self.assertEqual(p.nivel_general, 'alto')

    def test_nivel_general_medio_sin_ninguno_alto(self):
        p = self._make_pred(nivel_diabetes='medio')
        self.assertEqual(p.nivel_general, 'medio')

    def test_nivel_general_bajo_cuando_todos_bajo(self):
        p = self._make_pred()
        self.assertEqual(p.nivel_general, 'bajo')

    def test_nivel_general_alto_tiene_prioridad_sobre_medio(self):
        p = self._make_pred(nivel_diabetes='medio', nivel_cardiaco='alto')
        self.assertEqual(p.nivel_general, 'alto')


# ─────────────────────────────────────────────
# VISTA – nueva predicción
# ─────────────────────────────────────────────
class NuevaPrediccionViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = crear_usuario()
        self.datos = datos_clinicos(self.user)
        self.client.force_login(self.user)

    def test_nueva_prediccion_crea_registro(self):
        count_antes = Prediccion.objects.count()
        self.client.post(reverse('prediccion:nueva', args=[self.datos.pk]))
        self.assertEqual(Prediccion.objects.count(), count_antes + 1)

    def test_nueva_prediccion_redirige_a_resultado(self):
        r = self.client.post(reverse('prediccion:nueva', args=[self.datos.pk]))
        pred = Prediccion.objects.latest('fecha_prediccion')
        self.assertRedirects(r, reverse('prediccion:resultado', args=[pred.pk]),
                             fetch_redirect_response=False)

    def test_nueva_prediccion_requires_login(self):
        self.client.logout()
        r = self.client.post(reverse('prediccion:nueva', args=[self.datos.pk]))
        self.assertNotEqual(r.status_code, 200)

    def test_no_puede_predecir_datos_ajenos(self):
        otro = crear_usuario('otro@pred.com')
        datos_otro = datos_clinicos(otro)
        r = self.client.post(reverse('prediccion:nueva', args=[datos_otro.pk]))
        self.assertEqual(r.status_code, 404)

    def test_prediccion_duplicada_redirige_a_existente(self):
        """Segunda llamada no crea duplicado: redirige a la predicción ya guardada."""
        self.client.post(reverse('prediccion:nueva', args=[self.datos.pk]))
        count_antes = Prediccion.objects.count()
        self.client.post(reverse('prediccion:nueva', args=[self.datos.pk]))
        self.assertEqual(Prediccion.objects.count(), count_antes,
                         "Se creó una predicción duplicada para los mismos datos clínicos")

    def test_resultado_view_renderiza(self):
        self.client.post(reverse('prediccion:nueva', args=[self.datos.pk]))
        pred = Prediccion.objects.latest('fecha_prediccion')
        r = self.client.get(reverse('prediccion:resultado', args=[pred.pk]))
        self.assertEqual(r.status_code, 200)
        # Context debe contener las 5 enfermedades
        self.assertIn('enfermedades', r.context)
        self.assertEqual(len(r.context['enfermedades']), 5)

    def test_resultado_context_contiene_5_enfermedades_con_claves(self):
        self.client.post(reverse('prediccion:nueva', args=[self.datos.pk]))
        pred = Prediccion.objects.latest('fecha_prediccion')
        r = self.client.get(reverse('prediccion:resultado', args=[pred.pk]))
        for enf in r.context['enfermedades']:
            for key in ('nombre', 'riesgo', 'nivel', 'tiempo'):
                self.assertIn(key, enf, msg=f"Enfermedad sin clave '{key}'")

    def test_historial_predicciones_renderiza(self):
        r = self.client.get(reverse('prediccion:historial'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('predicciones', r.context)


# ─────────────────────────────────────────────
# SERVICE – _extraer_features
# ─────────────────────────────────────────────
class ExtraerFeaturesTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario('feat@pred.com')

    def test_retorna_array_numpy_shape_1x6(self):
        import numpy as np
        d = datos_clinicos(self.paciente, colesterol=200.0)
        X = service._extraer_features(d)
        self.assertEqual(X.shape, (1, 6))

    def test_orden_features_es_correcto(self):
        """Orden: age, bmi, glucose, systolic_bp, diastolic_bp, cholesterol."""
        d = datos_clinicos(
            self.paciente,
            edad=40, glucosa=100.0,
            presion_sistolica=120, presion_diastolica=80,
            colesterol=190.0,
        )
        X = service._extraer_features(d)
        self.assertEqual(X[0, 0], 40)           # age
        self.assertAlmostEqual(float(X[0, 2]), 100.0)  # glucose
        self.assertEqual(X[0, 3], 120)          # systolic_bp
        self.assertEqual(X[0, 4], 80)           # diastolic_bp
        self.assertAlmostEqual(float(X[0, 5]), 190.0)  # cholesterol

    def test_colesterol_none_usa_default(self):
        """Cuando colesterol es None, debe usar el valor por defecto (195)."""
        d = datos_clinicos(self.paciente, colesterol=None)
        X = service._extraer_features(d)
        self.assertGreater(float(X[0, 5]), 0, "colesterol None debe generar valor default >0")


# ─────────────────────────────────────────────
# SERVICE – estimar_tiempo_enfermedad
# ─────────────────────────────────────────────
class EstimarTiempoEnfermedadTest(TestCase):

    def test_riesgo_bajo_19_retorna_sin_riesgo(self):
        r = service.estimar_tiempo_enfermedad(19)
        self.assertEqual(r['urgencia'], 'bajo')
        self.assertIsNone(r['años'])

    def test_riesgo_85_o_mas_urgencia_alta_1_2_anios(self):
        r = service.estimar_tiempo_enfermedad(90)
        self.assertEqual(r['urgencia'], 'alto')
        self.assertIn('1', r['texto'])

    def test_riesgo_40_urgencia_media(self):
        r = service.estimar_tiempo_enfermedad(40)
        self.assertEqual(r['urgencia'], 'medio')

    def test_tendencia_subiendo_acorta_plazo(self):
        r_estable = service.estimar_tiempo_enfermedad(55, 'estable')
        r_sube    = service.estimar_tiempo_enfermedad(55, 'subiendo')
        self.assertLess(r_sube['años'], r_estable['años'],
                        "Tendencia 'subiendo' debe reducir el tiempo estimado")

    def test_tendencia_bajando_alarga_plazo(self):
        r_estable = service.estimar_tiempo_enfermedad(55, 'estable')
        r_baja    = service.estimar_tiempo_enfermedad(55, 'bajando')
        self.assertGreater(r_baja['años'], r_estable['años'],
                           "Tendencia 'bajando' debe aumentar el tiempo estimado")

    def test_retorna_claves_texto_urgencia_anios(self):
        r = service.estimar_tiempo_enfermedad(60)
        for key in ('texto', 'urgencia', 'años'):
            self.assertIn(key, r)


# ─────────────────────────────────────────────
# SERVICE – adjust_family_risk
# ─────────────────────────────────────────────
class AdjustFamilyRiskTest(TestCase):
    """
    Alta confiabilidad: valida los multiplicadores de antecedentes familiares
    basados en guías ADA/ESC/JNC 8. Un error aquí subestimaría el riesgo real
    de pacientes con historial familiar, con consecuencias clínicas graves.
    """

    BASE = {'diabetes': 0.10, 'hipertension': 0.08, 'renal': 0.05,
            'nafld': 0.15, 'cardiaco': 0.07}

    def test_sin_antecedentes_scores_no_cambian(self):
        resultado = service.adjust_family_risk(self.BASE, {})
        for k in self.BASE:
            self.assertAlmostEqual(resultado[k], self.BASE[k], places=5)

    def test_diabetes_uno_padre_multiplica_2_3(self):
        r = service.adjust_family_risk(self.BASE, {'diabetes_uno': True})
        esperado = min(1.0, self.BASE['diabetes'] * 2.3)
        self.assertAlmostEqual(r['diabetes'], esperado, places=5)

    def test_diabetes_ambos_padres_fija_60_pct(self):
        r = service.adjust_family_risk(self.BASE, {'diabetes_ambos': True})
        self.assertAlmostEqual(r['diabetes'], 0.60, places=5)

    def test_hta_ambos_padres_multiplica_4_5(self):
        r = service.adjust_family_risk(self.BASE, {'hipertension_ambos': True})
        esperado = min(1.0, self.BASE['hipertension'] * 4.5)
        self.assertAlmostEqual(r['hipertension'], esperado, places=5)

    def test_renal_con_comorbilidades_factor_3(self):
        """Renal + (DM > 50% o HTA > 50%) → factor 3.0 (2.5 + 0.5)."""
        scores = dict(self.BASE, renal=0.10)
        ctx = {'riesgo_diabetes': 0.6}   # DM > 50%
        r = service.adjust_family_risk(scores, {'renal': True}, contexto=ctx)
        esperado = min(1.0, 0.10 * 3.0)
        self.assertAlmostEqual(r['renal'], esperado, places=5)

    def test_nafld_sin_sobrepeso_no_multiplica(self):
        """NAFLD solo se amplifica con antecedente + IMC > 25."""
        ctx = {'imc': 22.0}   # IMC normal → no se multiplica
        r = service.adjust_family_risk(self.BASE, {'nafld': True}, contexto=ctx)
        self.assertAlmostEqual(r['nafld'], self.BASE['nafld'], places=5)

    def test_nafld_con_sobrepeso_multiplica_1_7(self):
        ctx = {'imc': 28.0}
        r = service.adjust_family_risk(self.BASE, {'nafld': True}, contexto=ctx)
        esperado = min(1.0, self.BASE['nafld'] * 1.7)
        self.assertAlmostEqual(r['nafld'], esperado, places=5)

    def test_cardiaco_multiplica_1_7(self):
        r = service.adjust_family_risk(self.BASE, {'cardiaco': True})
        esperado = min(1.0, self.BASE['cardiaco'] * 1.7)
        self.assertAlmostEqual(r['cardiaco'], esperado, places=5)

    def test_scores_nunca_superan_1_0(self):
        scores_altos = {'diabetes': 0.9, 'hipertension': 0.9, 'renal': 0.9,
                        'nafld': 0.9, 'cardiaco': 0.9}
        antec = {'diabetes_ambos': True, 'hipertension_ambos': True}
        r = service.adjust_family_risk(scores_altos, antec)
        for k, v in r.items():
            self.assertLessEqual(v, 1.0, msg=f"{k} supera 1.0: {v}")

    def test_scores_siempre_positivos(self):
        r = service.adjust_family_risk({'diabetes': 0.0}, {'diabetes_uno': True})
        self.assertGreaterEqual(r['diabetes'], 0.0)


# ─────────────────────────────────────────────
# API REST – api_analizar (DRF)
# ─────────────────────────────────────────────
class ApiAnalizarTest(TestCase):
    """
    Alta confiabilidad: prueba el endpoint REST POST /prediccion/api/analizar/
    con APIClient de DRF. Valida tipos de datos (float para porcentajes),
    estructura de respuesta y autenticación, garantizando que integraciones
    externas (apps móviles, otros sistemas) reciban datos clínicamente correctos.
    """

    def setUp(self):
        self.api_client = APIClient()
        self.user = crear_usuario('api@pred.com')
        self.datos = datos_clinicos(self.user)
        self.url = reverse('prediccion:api_analizar')

    def test_sin_autenticacion_retorna_401_o_403(self):
        r = self.api_client.post(self.url, {'datos_pk': self.datos.pk}, format='json')
        self.assertIn(r.status_code, (401, 403))

    def test_sin_datos_pk_retorna_400(self):
        self.api_client.force_authenticate(user=self.user)
        r = self.api_client.post(self.url, {}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_datos_ajenos_retorna_404(self):
        otro = crear_usuario('otro_api@pred.com')
        datos_otro = datos_clinicos(otro)
        self.api_client.force_authenticate(user=self.user)
        r = self.api_client.post(self.url, {'datos_pk': datos_otro.pk}, format='json')
        self.assertEqual(r.status_code, 404)

    def test_prediccion_exitosa_retorna_201(self):
        self.api_client.force_authenticate(user=self.user)
        r = self.api_client.post(self.url, {'datos_pk': self.datos.pk}, format='json')
        self.assertEqual(r.status_code, 201)

    def test_respuesta_contiene_claves_de_las_5_enfermedades(self):
        self.api_client.force_authenticate(user=self.user)
        r = self.api_client.post(self.url, {'datos_pk': self.datos.pk}, format='json')
        data = r.json()
        claves_esperadas = [
            'riesgo_diabetes', 'nivel_diabetes',
            'riesgo_hipertension', 'nivel_hipertension',
            'riesgo_renal', 'nivel_renal',
            'riesgo_nafld', 'nivel_nafld',
            'riesgo_cardiaco', 'nivel_cardiaco',
            'modelo_version', 'prediccion_pk',
        ]
        for clave in claves_esperadas:
            self.assertIn(clave, data, msg=f"Falta clave '{clave}' en respuesta API")

    def test_porcentajes_son_floats_entre_0_y_100(self):
        """Garantiza que la API devuelve floats (no strings) para las probabilidades."""
        self.api_client.force_authenticate(user=self.user)
        r = self.api_client.post(self.url, {'datos_pk': self.datos.pk}, format='json')
        data = r.json()
        for campo in ('riesgo_diabetes', 'riesgo_hipertension', 'riesgo_renal',
                      'riesgo_nafld', 'riesgo_cardiaco'):
            val = data[campo]
            self.assertIsInstance(val, (int, float),
                                  msg=f"'{campo}' debe ser número, recibido: {type(val)}")
            self.assertGreaterEqual(val, 0,   msg=f"'{campo}' = {val} es negativo")
            self.assertLessEqual(val,   99.9, msg=f"'{campo}' = {val} supera 99.9")

    def test_niveles_son_valores_validos(self):
        self.api_client.force_authenticate(user=self.user)
        r = self.api_client.post(self.url, {'datos_pk': self.datos.pk}, format='json')
        data = r.json()
        valores_validos = {'bajo', 'medio', 'alto'}
        for campo in ('nivel_diabetes', 'nivel_hipertension', 'nivel_renal',
                      'nivel_nafld', 'nivel_cardiaco'):
            self.assertIn(data[campo], valores_validos,
                          msg=f"'{campo}' tiene valor inválido: {data[campo]}")

    def test_antecedentes_aplicados_aumentan_riesgo(self):
        """
        Con antecedente de diabetes en ambos padres, el score de diabetes
        debe ser ≥ 60% según las guías ADA, independientemente del valor base.
        """
        self.api_client.force_authenticate(user=self.user)
        payload = {
            'datos_pk': self.datos.pk,
            'antecedentes': {'diabetes_ambos': True},
        }
        r = self.api_client.post(self.url, payload, format='json')
        data = r.json()
        self.assertEqual(r.status_code, 201)
        self.assertTrue(data.get('antecedentes_aplicados', False))
        self.assertGreaterEqual(data['riesgo_diabetes'], 60.0,
                                "Diabetes con ambos padres debe dar ≥ 60%")
