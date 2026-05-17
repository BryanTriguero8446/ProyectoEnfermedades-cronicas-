from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from usuarios.models import Usuario
from clinico.models import DatosClinico


def crear_usuario(correo='pac@test.com', password='Pass1234!'):
    return Usuario.objects.create_user(
        correo=correo, nombre='Juan', apellido='Pérez', password=password
    )


def datos_base(paciente, **kwargs):
    """Crea y guarda un DatosClinico con valores válidos por defecto."""
    defaults = dict(
        paciente=paciente,
        edad=35, peso=70.0, altura=1.75,
        presion_sistolica=120, presion_diastolica=80,
        glucosa=90.0, frecuencia_cardiaca=72,
        actividad_fisica='moderado',
    )
    defaults.update(kwargs)
    obj = DatosClinico(**defaults)
    obj.save()
    return obj


# ─────────────────────────────────────────────
# MODELO – Cálculo de IMC
# ─────────────────────────────────────────────
class DatosClinicoIMCTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()

    def test_imc_calculado_al_guardar(self):
        d = datos_base(self.paciente, peso=70.0, altura=1.75)
        esperado = round(70.0 / (1.75 ** 2), 2)
        self.assertAlmostEqual(float(d.imc), esperado, places=1)

    def test_imc_recalculado_al_actualizar(self):
        d = datos_base(self.paciente, peso=70.0, altura=1.75)
        d.peso = 90.0
        d.save()
        esperado = round(90.0 / (1.75 ** 2), 2)
        self.assertAlmostEqual(float(d.imc), esperado, places=1)

    def test_imc_no_calculado_si_altura_cero(self):
        # altura=0 no debería producir ZeroDivisionError; IMC queda None
        d = DatosClinico(
            paciente=self.paciente,
            edad=30, peso=70.0, altura=0,
            presion_sistolica=120, presion_diastolica=80,
            glucosa=90.0, frecuencia_cardiaca=72,
        )
        d.save()
        self.assertIsNone(d.imc)

    def test_imc_precision_dos_decimales(self):
        d = datos_base(self.paciente, peso=68.5, altura=1.72)
        self.assertIsNotNone(d.imc)
        partes = str(float(d.imc)).split('.')
        self.assertLessEqual(len(partes[1]) if len(partes) > 1 else 0, 2)


# ─────────────────────────────────────────────
# MODELO – clasificacion_imc
# ─────────────────────────────────────────────
class ClasificacionIMCTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()

    def _make(self, imc_val):
        d = datos_base(self.paciente)
        d.imc = imc_val
        return d

    def test_bajo_peso(self):
        self.assertEqual(self._make(17.0).clasificacion_imc, 'Bajo peso')

    def test_normal(self):
        self.assertEqual(self._make(22.0).clasificacion_imc, 'Normal')

    def test_sobrepeso(self):
        self.assertEqual(self._make(27.0).clasificacion_imc, 'Sobrepeso')

    def test_obesidad_1(self):
        self.assertEqual(self._make(32.0).clasificacion_imc, 'Obesidad I')

    def test_obesidad_2(self):
        self.assertEqual(self._make(37.0).clasificacion_imc, 'Obesidad II')

    def test_obesidad_3(self):
        self.assertEqual(self._make(42.0).clasificacion_imc, 'Obesidad III')

    def test_limite_exacto_185_es_normal(self):
        # 18.5 NO es < 18.5, debe caer en Normal
        self.assertEqual(self._make(18.5).clasificacion_imc, 'Normal')

    def test_limite_exacto_25_es_sobrepeso(self):
        # 25.0 NO es < 25, debe caer en Sobrepeso
        self.assertEqual(self._make(25.0).clasificacion_imc, 'Sobrepeso')

    def test_limite_exacto_30_es_obesidad_1(self):
        self.assertEqual(self._make(30.0).clasificacion_imc, 'Obesidad I')

    def test_sin_dato_cuando_imc_none(self):
        d = datos_base(self.paciente)
        d.imc = None
        self.assertEqual(d.clasificacion_imc, 'Sin dato')


# ─────────────────────────────────────────────
# MODELO – clasificacion_glucosa
# ─────────────────────────────────────────────
class ClasificacionGlucosaTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()

    def _make(self, glucosa):
        d = datos_base(self.paciente, glucosa=glucosa)
        return d

    def test_glucosa_baja(self):
        label, color = self._make(60).clasificacion_glucosa
        self.assertEqual(label, 'baja')
        self.assertEqual(color, 'warning')

    def test_glucosa_normal(self):
        label, color = self._make(85).clasificacion_glucosa
        self.assertEqual(label, 'normal')
        self.assertEqual(color, 'success')

    def test_glucosa_limite_100_es_normal(self):
        label, _ = self._make(100).clasificacion_glucosa
        self.assertEqual(label, 'normal')

    def test_glucosa_prediabetes(self):
        label, color = self._make(110).clasificacion_glucosa
        self.assertEqual(label, 'prediabetes')
        self.assertEqual(color, 'warning')

    def test_glucosa_alta(self):
        label, color = self._make(130).clasificacion_glucosa
        self.assertEqual(label, 'alta')
        self.assertEqual(color, 'danger')


# ─────────────────────────────────────────────
# MODELO – clasificacion_presion
# ─────────────────────────────────────────────
class ClasificacionPresionTest(TestCase):

    def setUp(self):
        self.paciente = crear_usuario()

    def _make(self, sis, dia):
        d = datos_base(self.paciente, presion_sistolica=sis, presion_diastolica=dia)
        return d

    def test_presion_normal(self):
        label, color = self._make(115, 75).clasificacion_presion
        self.assertEqual(label, 'normal')
        self.assertEqual(color, 'success')

    def test_presion_elevada(self):
        label, color = self._make(125, 75).clasificacion_presion
        self.assertEqual(label, 'elevada')
        self.assertEqual(color, 'warning')

    def test_hipertension_1_sis(self):
        label, color = self._make(135, 75).clasificacion_presion
        self.assertEqual(label, 'hipertensión I')

    def test_hipertension_2(self):
        label, color = self._make(145, 95).clasificacion_presion
        self.assertEqual(label, 'hipertensión II')
        self.assertEqual(color, 'danger')

    def test_limite_exacto_120_sistolica(self):
        # s=120 no es < 120 → no es "normal"; d=79 < 80 → "elevada"
        label, _ = self._make(120, 79).clasificacion_presion
        self.assertNotEqual(label, 'normal')


# ─────────────────────────────────────────────
# VISTAS – nuevo_registro
# ─────────────────────────────────────────────
class NuevoRegistroViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = crear_usuario()
        self.client.force_login(self.user)
        self.url = reverse('clinico:nuevo_registro')
        self.post_data = {
            'edad': '35', 'peso': '70.0', 'altura': '1.75',
            'presion_sistolica': '120', 'presion_diastolica': '80',
            'glucosa': '90.0', 'frecuencia_cardiaca': '72',
            'actividad_fisica': 'moderado',
        }

    def test_get_renders_form(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_requires_login(self):
        self.client.logout()
        r = self.client.get(self.url)
        self.assertNotEqual(r.status_code, 200)

    def test_post_valid_data_creates_record(self):
        count_antes = DatosClinico.objects.count()
        r = self.client.post(self.url, self.post_data)
        self.assertEqual(DatosClinico.objects.count(), count_antes + 1)

    def test_post_valid_data_redirects_to_detalle(self):
        r = self.client.post(self.url, self.post_data)
        nuevo = DatosClinico.objects.latest('fecha_registro')
        self.assertRedirects(r, reverse('clinico:detalle', args=[nuevo.pk]),
                             fetch_redirect_response=False)

    def test_post_missing_required_field_shows_error(self):
        data = dict(self.post_data)
        del data['glucosa']
        r = self.client.post(self.url, data)
        # debe permanecer en el formulario, no crear registro
        self.assertEqual(r.status_code, 200)
        self.assertEqual(DatosClinico.objects.count(), 0)

    def test_post_non_numeric_edad_shows_error(self):
        data = dict(self.post_data)
        data['edad'] = 'abc'
        r = self.client.post(self.url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(DatosClinico.objects.count(), 0)

    def test_post_optional_labs_saved_when_provided(self):
        data = dict(self.post_data)
        data.update({'colesterol': '190', 'trigliceridos': '140', 'creatinina': '0.9'})
        self.client.post(self.url, data)
        d = DatosClinico.objects.latest('fecha_registro')
        self.assertAlmostEqual(float(d.colesterol), 190.0)
        self.assertAlmostEqual(float(d.trigliceridos), 140.0)
        self.assertAlmostEqual(float(d.creatinina), 0.9)

    def test_post_optional_labs_none_when_empty(self):
        self.client.post(self.url, self.post_data)
        d = DatosClinico.objects.latest('fecha_registro')
        self.assertIsNone(d.colesterol)
        self.assertIsNone(d.trigliceridos)
        self.assertIsNone(d.creatinina)

    def test_fumador_checkbox_on(self):
        data = dict(self.post_data)
        data['fumador'] = 'on'
        self.client.post(self.url, data)
        d = DatosClinico.objects.latest('fecha_registro')
        self.assertTrue(d.fumador)

    def test_fumador_checkbox_off(self):
        # Sin el campo 'fumador' en POST → debe ser False
        self.client.post(self.url, self.post_data)
        d = DatosClinico.objects.latest('fecha_registro')
        self.assertFalse(d.fumador)

    def test_validadores_rechazan_edad_fuera_de_rango(self):
        """
        Verifica que edad=999 sea rechazada por full_clean() y NO se guarde.
        El view debe llamar full_clean() antes de save() para que los
        MaxValueValidator/MinValueValidator del modelo funcionen.
        """
        data = dict(self.post_data)
        data['edad'] = '999'
        r = self.client.post(self.url, data)
        # No debe guardarse ningún registro con edad fuera de rango
        self.assertEqual(DatosClinico.objects.filter(edad=999).count(), 0,
                         "edad=999 fue guardada: full_clean() no está siendo llamado")
        # Debe mostrar el formulario con error (código 200)
        self.assertEqual(r.status_code, 200)


# ─────────────────────────────────────────────
# VISTAS – historial y detalle
# ─────────────────────────────────────────────
class HistorialDetalleViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user1 = crear_usuario('u1@test.com')
        self.user2 = crear_usuario('u2@test.com')
        self.registro = datos_base(self.user1)

    def test_historial_requires_login(self):
        r = self.client.get(reverse('clinico:historial'))
        self.assertNotEqual(r.status_code, 200)

    def test_historial_shows_own_records(self):
        self.client.force_login(self.user1)
        r = self.client.get(reverse('clinico:historial'))
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.registro, r.context['registros'])

    def test_historial_no_muestra_registros_ajenos(self):
        self.client.force_login(self.user2)
        r = self.client.get(reverse('clinico:historial'))
        self.assertNotIn(self.registro, r.context['registros'])

    def test_detalle_propio_accesible(self):
        self.client.force_login(self.user1)
        r = self.client.get(reverse('clinico:detalle', args=[self.registro.pk]))
        self.assertEqual(r.status_code, 200)

    def test_detalle_ajeno_retorna_404(self):
        self.client.force_login(self.user2)
        r = self.client.get(reverse('clinico:detalle', args=[self.registro.pk]))
        self.assertEqual(r.status_code, 404)


# ─────────────────────────────────────────────
# API JSON
# ─────────────────────────────────────────────
class ApiHistorialJsonTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = crear_usuario()
        datos_base(self.user, glucosa=95.0)
        datos_base(self.user, glucosa=110.0)

    def test_api_requires_login(self):
        r = self.client.get(reverse('clinico:api_historial'))
        self.assertNotEqual(r.status_code, 200)

    def test_api_returns_json(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse('clinico:api_historial'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/json')

    def test_api_json_keys_presentes(self):
        self.client.force_login(self.user)
        import json
        data = json.loads(self.client.get(reverse('clinico:api_historial')).content)
        for key in ('labels', 'glucosa', 'presion_sistolica',
                    'presion_diastolica', 'imc', 'frecuencia_cardiaca'):
            self.assertIn(key, data, msg=f"Falta clave '{key}' en API JSON")

    def test_api_devuelve_solo_datos_propios(self):
        otro = crear_usuario('otro@test.com')
        datos_base(otro, glucosa=200.0)
        self.client.force_login(self.user)
        import json
        data = json.loads(self.client.get(reverse('clinico:api_historial')).content)
        self.assertNotIn(200.0, data['glucosa'])
