import time
from django.test import TestCase, Client
from django.urls import reverse
from usuarios.models import Usuario
from clinico.models import DatosClinico


UMBRAL_PAGINA_MS  = 2000   # páginas HTML: máx 2 s
UMBRAL_API_MS     = 1000   # endpoints JSON: máx 1 s
UMBRAL_API_FAST   = 500    # endpoints simples: máx 0.5 s


def crear_paciente(correo='perf@test.com'):
    u = Usuario.objects.create_user(
        correo=correo, nombre='Ana', apellido='Perf', password='Pass1234!'
    )
    u.email_verificado = True
    u.save(update_fields=['email_verificado'])
    return u


def datos_base(paciente, **kw):
    defaults = dict(
        paciente=paciente, edad=35, peso=70.0, altura=1.75,
        presion_sistolica=120, presion_diastolica=80,
        glucosa=90.0, frecuencia_cardiaca=72, actividad_fisica='moderado',
    )
    defaults.update(kw)
    d = DatosClinico(**defaults)
    d.save()
    return d


class RendimientoPaginasTest(TestCase):
    """Verifica que las páginas principales respondan dentro del umbral."""

    def setUp(self):
        self.client = Client()
        self.user = crear_paciente()
        self.client.force_login(self.user)

    def _medir(self, url):
        inicio = time.perf_counter()
        r = self.client.get(url)
        ms = (time.perf_counter() - inicio) * 1000
        return ms, r

    def test_login_page_bajo_umbral(self):
        self.client.logout()
        ms, r = self._medir(reverse('usuarios:login'))
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, UMBRAL_PAGINA_MS,
                        f"Login tardó {ms:.0f} ms — límite {UMBRAL_PAGINA_MS} ms")

    def test_registro_page_bajo_umbral(self):
        self.client.logout()
        ms, r = self._medir(reverse('usuarios:registro'))
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, UMBRAL_PAGINA_MS,
                        f"Registro tardó {ms:.0f} ms")

    def test_dashboard_bajo_umbral(self):
        ms, r = self._medir(reverse('usuarios:dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, UMBRAL_PAGINA_MS,
                        f"Dashboard tardó {ms:.0f} ms")

    def test_historial_bajo_umbral(self):
        datos_base(self.user)
        datos_base(self.user)
        ms, r = self._medir(reverse('clinico:historial'))
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, UMBRAL_PAGINA_MS,
                        f"Historial tardó {ms:.0f} ms")

    def test_nuevo_registro_bajo_umbral(self):
        ms, r = self._medir(reverse('clinico:nuevo_registro'))
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, UMBRAL_PAGINA_MS,
                        f"Nuevo registro tardó {ms:.0f} ms")

    def test_alertas_lista_bajo_umbral(self):
        ms, r = self._medir(reverse('alertas:lista'))
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, UMBRAL_PAGINA_MS,
                        f"Alertas tardó {ms:.0f} ms")

    def test_reportes_lista_bajo_umbral(self):
        ms, r = self._medir(reverse('reportes:lista'))
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, UMBRAL_PAGINA_MS,
                        f"Reportes tardó {ms:.0f} ms")


class RendimientoAPITest(TestCase):
    """Verifica que los endpoints JSON/CSV respondan más rápido que las páginas."""

    def setUp(self):
        self.client = Client()
        self.user = crear_paciente()
        self.client.force_login(self.user)
        datos_base(self.user)

    def _medir(self, url):
        inicio = time.perf_counter()
        r = self.client.get(url)
        ms = (time.perf_counter() - inicio) * 1000
        return ms, r

    def test_api_historial_json_bajo_1s(self):
        ms, r = self._medir(reverse('clinico:api_historial'))
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, UMBRAL_API_MS,
                        f"API historial tardó {ms:.0f} ms — límite {UMBRAL_API_MS} ms")

    def test_api_alertas_count_bajo_500ms(self):
        ms, r = self._medir(reverse('alertas:api_count'))
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, UMBRAL_API_FAST,
                        f"API count tardó {ms:.0f} ms — límite {UMBRAL_API_FAST} ms")

    def test_csv_clinico_bajo_2s(self):
        ms, r = self._medir(reverse('reportes:csv_clinico'))
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, UMBRAL_PAGINA_MS,
                        f"CSV clínico tardó {ms:.0f} ms")
