from django.test import TestCase, Client
from django.urls import reverse
from usuarios.models import Usuario
from clinico.models import DatosClinico
from alertas.models import Alerta
from prediccion.service import generar_alertas


def crear_usuario(correo='alerta@test.com'):
    return Usuario.objects.create_user(
        correo=correo, nombre='Pedro', apellido='Test', password='Pass1234!'
    )


def datos_base(paciente, **kwargs):
    defaults = dict(
        paciente=paciente,
        edad=35, peso=70.0, altura=1.75,
        presion_sistolica=115, presion_diastolica=75,
        glucosa=90.0, frecuencia_cardiaca=72,
        actividad_fisica='moderado',
    )
    defaults.update(kwargs)
    d = DatosClinico(**defaults)
    d.save()
    return d


# ─────────────────────────────────────────────
# generar_alertas() – lógica clínica
# ─────────────────────────────────────────────
class GenerarAlertasGlucosaTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()

    def test_glucosa_normal_no_genera_alerta(self):
        d = datos_base(self.paciente, glucosa=90.0)
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertNotIn('glucosa_alta', tipos)
        self.assertNotIn('glucosa_baja', tipos)

    def test_glucosa_alta_danger_sobre_126(self):
        d = datos_base(self.paciente, glucosa=150.0)
        alertas = generar_alertas(d, {})
        match = [a for a in alertas if a['tipo'] == 'glucosa_alta']
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]['severidad'], 'danger')

    def test_glucosa_alta_warning_entre_100_y_126(self):
        d = datos_base(self.paciente, glucosa=115.0)
        alertas = generar_alertas(d, {})
        match = [a for a in alertas if a['tipo'] == 'glucosa_alta']
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]['severidad'], 'warning')

    def test_glucosa_baja_hipoglucemia(self):
        d = datos_base(self.paciente, glucosa=55.0)
        alertas = generar_alertas(d, {})
        match = [a for a in alertas if a['tipo'] == 'glucosa_baja']
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]['severidad'], 'danger')

    def test_glucosa_limite_100_no_es_alta(self):
        d = datos_base(self.paciente, glucosa=100.0)
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertNotIn('glucosa_alta', tipos)

    def test_glucosa_exactamente_70_no_es_baja(self):
        d = datos_base(self.paciente, glucosa=70.0)
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertNotIn('glucosa_baja', tipos)


class GenerarAlertasPresionTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()

    def test_presion_normal_no_genera_alerta(self):
        d = datos_base(self.paciente, presion_sistolica=115, presion_diastolica=75)
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertNotIn('presion_alta', tipos)

    def test_hipertension_danger_sis_140_o_dia_90(self):
        d = datos_base(self.paciente, presion_sistolica=145, presion_diastolica=95)
        alertas = generar_alertas(d, {})
        match = [a for a in alertas if a['tipo'] == 'presion_alta']
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]['severidad'], 'danger')

    def test_presion_elevada_warning_sis_130_dia_menor_90(self):
        d = datos_base(self.paciente, presion_sistolica=132, presion_diastolica=78)
        alertas = generar_alertas(d, {})
        match = [a for a in alertas if a['tipo'] == 'presion_alta']
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]['severidad'], 'warning')

    def test_presion_limite_exacto_dia_90_es_danger(self):
        d = datos_base(self.paciente, presion_sistolica=120, presion_diastolica=90)
        alertas = generar_alertas(d, {})
        match = [a for a in alertas if a['tipo'] == 'presion_alta']
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]['severidad'], 'danger')


class GenerarAlertasIMCTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()

    def test_imc_normal_no_genera_alerta(self):
        d = datos_base(self.paciente, peso=70.0, altura=1.75)  # IMC≈22.86
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertNotIn('imc_alto', tipos)
        self.assertNotIn('imc_bajo', tipos)

    def test_obesidad_genera_alerta_imc_alto(self):
        d = datos_base(self.paciente, peso=100.0, altura=1.70)  # IMC≈34.6
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertIn('imc_alto', tipos)

    def test_bajo_peso_genera_alerta_imc_bajo(self):
        d = datos_base(self.paciente, peso=45.0, altura=1.70)  # IMC≈15.6
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertIn('imc_bajo', tipos)

    def test_imc_justo_en_30_genera_alerta_alto(self):
        d = datos_base(self.paciente, peso=86.7, altura=1.70)  # IMC≈30.0
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertIn('imc_alto', tipos)


class GenerarAlertasFCTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()

    def test_fc_normal_no_genera_alerta(self):
        d = datos_base(self.paciente, frecuencia_cardiaca=72)
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertNotIn('frecuencia_anormal', tipos)

    def test_taquicardia_fc_mayor_100(self):
        d = datos_base(self.paciente, frecuencia_cardiaca=105)
        alertas = generar_alertas(d, {})
        match = [a for a in alertas if a['tipo'] == 'frecuencia_anormal']
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]['severidad'], 'warning')

    def test_bradicardia_fc_59(self):
        d = datos_base(self.paciente, frecuencia_cardiaca=59)
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertIn('frecuencia_anormal', tipos)

    def test_fc_limite_60_no_genera_alerta_bradicardia(self):
        d = datos_base(self.paciente, frecuencia_cardiaca=60)
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertNotIn('frecuencia_anormal', tipos)

    def test_fc_limite_100_no_genera_alerta_taquicardia(self):
        d = datos_base(self.paciente, frecuencia_cardiaca=100)
        alertas = generar_alertas(d, {})
        tipos = [a['tipo'] for a in alertas]
        self.assertNotIn('frecuencia_anormal', tipos)


class GenerarAlertasRiesgoPrediccionTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()
        self.datos = datos_base(self.paciente)

    def test_riesgo_alto_diabetes_genera_alerta(self):
        pred_data = {
            'riesgo_diabetes': 80.0, 'nivel_diabetes': 'alto',
            'riesgo_hipertension': 10, 'nivel_hipertension': 'bajo',
            'riesgo_renal': 5, 'nivel_renal': 'bajo',
            'riesgo_nafld': 5, 'nivel_nafld': 'bajo',
            'riesgo_cardiaco': 5, 'nivel_cardiaco': 'bajo',
        }
        alertas = generar_alertas(self.datos, pred_data)
        tipos = [a['tipo'] for a in alertas]
        self.assertIn('riesgo_alto_diabetes', tipos)

    def test_nivel_medio_no_genera_alerta_riesgo(self):
        pred_data = {
            'riesgo_diabetes': 50.0, 'nivel_diabetes': 'medio',
            'riesgo_hipertension': 10, 'nivel_hipertension': 'bajo',
            'riesgo_renal': 5, 'nivel_renal': 'bajo',
            'riesgo_nafld': 5, 'nivel_nafld': 'bajo',
            'riesgo_cardiaco': 5, 'nivel_cardiaco': 'bajo',
        }
        alertas = generar_alertas(self.datos, pred_data)
        tipos = [a['tipo'] for a in alertas]
        self.assertNotIn('riesgo_alto_diabetes', tipos)

    def test_sin_prediccion_data_no_explota(self):
        alertas = generar_alertas(self.datos, {})
        self.assertIsInstance(alertas, list)


# ─────────────────────────────────────────────
# MODELO Alerta – propiedades
# ─────────────────────────────────────────────
class AlertaModelTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()

    def _make(self, severidad):
        return Alerta(
            paciente=self.paciente,
            tipo='glucosa_alta',
            severidad=severidad,
            mensaje='Test',
        )

    def test_icono_info(self):
        self.assertIn('info', self._make('info').icono)

    def test_icono_warning(self):
        self.assertIn('triangle', self._make('warning').icono)

    def test_icono_danger(self):
        self.assertIn('octagon', self._make('danger').icono)

    def test_color_badge_info(self):
        self.assertEqual(self._make('info').color_badge, 'primary')

    def test_color_badge_warning(self):
        self.assertEqual(self._make('warning').color_badge, 'warning')

    def test_color_badge_danger(self):
        self.assertEqual(self._make('danger').color_badge, 'danger')

    def test_alerta_no_leida_por_defecto(self):
        a = Alerta.objects.create(
            paciente=self.paciente, tipo='glucosa_alta',
            severidad='warning', mensaje='Test',
        )
        self.assertFalse(a.leida)


# ─────────────────────────────────────────────
# VISTAS – lista, marcar, API count
# ─────────────────────────────────────────────
class AlertaViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = crear_usuario()
        self.client.force_login(self.user)
        self.datos = datos_base(self.user)
        self.alerta = Alerta.objects.create(
            paciente=self.user, tipo='glucosa_alta',
            severidad='warning', mensaje='Glucosa alta test',
        )

    def test_lista_alertas_requiere_login(self):
        self.client.logout()
        r = self.client.get(reverse('alertas:lista'))
        self.assertNotEqual(r.status_code, 200)

    def test_lista_alertas_renderiza(self):
        r = self.client.get(reverse('alertas:lista'))
        self.assertEqual(r.status_code, 200)

    def test_marcar_leida_actualiza_estado(self):
        self.assertFalse(self.alerta.leida)
        self.client.post(reverse('alertas:marcar_leida', args=[self.alerta.pk]))
        self.alerta.refresh_from_db()
        self.assertTrue(self.alerta.leida)

    def test_marcar_todas_leidas(self):
        Alerta.objects.create(
            paciente=self.user, tipo='presion_alta',
            severidad='danger', mensaje='Presión alta test',
        )
        self.client.post(reverse('alertas:marcar_todas'))
        no_leidas = Alerta.objects.filter(paciente=self.user, leida=False).count()
        self.assertEqual(no_leidas, 0)

    def test_api_count_retorna_json(self):
        r = self.client.get(reverse('alertas:api_count'))
        self.assertEqual(r.status_code, 200)
        import json
        data = json.loads(r.content)
        self.assertIn('count', data)

    def test_api_count_correcto(self):
        import json
        r = self.client.get(reverse('alertas:api_count'))
        data = json.loads(r.content)
        self.assertEqual(data['count'], 1)

    def test_api_count_cero_tras_marcar_todas(self):
        import json
        self.client.post(reverse('alertas:marcar_todas'))
        r = self.client.get(reverse('alertas:api_count'))
        data = json.loads(r.content)
        self.assertEqual(data['count'], 0)

    def test_no_puede_ver_alertas_ajenas(self):
        otro = crear_usuario('otro@alerta.com')
        alerta_otro = Alerta.objects.create(
            paciente=otro, tipo='imc_alto',
            severidad='warning', mensaje='Alerta ajena',
        )
        r = self.client.get(reverse('alertas:lista'))
        alertas_ctx = list(r.context.get('alertas', []))
        self.assertNotIn(alerta_otro, alertas_ctx)
