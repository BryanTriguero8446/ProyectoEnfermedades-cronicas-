from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
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
