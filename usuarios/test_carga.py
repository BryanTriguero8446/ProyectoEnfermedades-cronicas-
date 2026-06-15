from django.test import TestCase, Client
from django.urls import reverse
from usuarios.models import Usuario
from clinico.models import DatosClinico


def crear_paciente(correo='carga@test.com'):
    u = Usuario.objects.create_user(
        correo=correo, nombre='Carga', apellido='Test', password='Pass1234!'
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


POST_CLINICO = {
    'edad': '35', 'peso': '70.0', 'altura': '1.75',
    'presion_sistolica': '120', 'presion_diastolica': '80',
    'glucosa': '90.0', 'frecuencia_cardiaca': '72',
    'actividad_fisica': 'moderado',
}


class CargaLoginTest(TestCase):
    """Simula múltiples requests al endpoint de login."""

    def test_50_requests_consecutivos_login(self):
        errores = 0
        for _ in range(50):
            r = self.client.get(reverse('usuarios:login'))
            if r.status_code != 200:
                errores += 1
        self.assertEqual(errores, 0,
                         f"Login falló {errores}/50 requests consecutivos")

    def test_20_intentos_login_fallido_no_bloquea_servidor(self):
        for i in range(20):
            r = self.client.post(reverse('usuarios:login'), {
                'correo': f'noexiste{i}@test.com',
                'password': 'wrong'
            })
            self.assertEqual(r.status_code, 200,
                             f"Servidor cayó en intento {i+1}")


class CargaDashboardTest(TestCase):
    """Simula un usuario que recarga el dashboard repetidamente."""

    def setUp(self):
        self.client = Client()
        self.user = crear_paciente()
        self.client.force_login(self.user)

    def test_30_recargas_dashboard(self):
        errores = 0
        for _ in range(30):
            r = self.client.get(reverse('usuarios:dashboard'))
            if r.status_code != 200:
                errores += 1
        self.assertEqual(errores, 0,
                         f"Dashboard falló {errores}/30 recargas")

    def test_20_consultas_api_json(self):
        errores = 0
        for _ in range(20):
            r = self.client.get(reverse('clinico:api_historial'))
            if r.status_code != 200:
                errores += 1
        self.assertEqual(errores, 0,
                         f"API historial falló {errores}/20 consultas")

    def test_20_consultas_api_count_alertas(self):
        errores = 0
        for _ in range(20):
            r = self.client.get(reverse('alertas:api_count'))
            if r.status_code != 200:
                errores += 1
        self.assertEqual(errores, 0,
                         f"API count alertas falló {errores}/20 consultas")


class CargaRegistrosClinicosTest(TestCase):
    """Simula un paciente que crea múltiples registros clínicos en sucesión."""

    def setUp(self):
        self.client = Client()
        self.user = crear_paciente()
        self.client.force_login(self.user)

    def test_10_registros_clinicos_sucesivos(self):
        url = reverse('clinico:nuevo_registro')
        count_antes = DatosClinico.objects.count()
        for _ in range(10):
            self.client.post(url, POST_CLINICO)
        self.assertEqual(DatosClinico.objects.count(), count_antes + 10,
                         "No se crearon los 10 registros clínicos sucesivos")

    def test_historial_con_50_registros_responde(self):
        for _ in range(50):
            datos_base(self.user)
        r = self.client.get(reverse('clinico:historial'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['registros']), 50)


class EstresMultiUsuarioTest(TestCase):
    """Simula múltiples usuarios distintos accediendo al sistema."""

    def test_10_usuarios_distintos_acceden_dashboard(self):
        errores = 0
        for i in range(10):
            u = Usuario.objects.create_user(
                correo=f'user{i}@stress.com',
                nombre=f'User{i}', apellido='Test',
                password='Pass1234!'
            )
            u.email_verificado = True
            u.save(update_fields=['email_verificado'])

            c = Client()
            c.force_login(u)
            r = c.get(reverse('usuarios:dashboard'))
            if r.status_code != 200:
                errores += 1

        self.assertEqual(errores, 0,
                         f"{errores}/10 usuarios no pudieron acceder al dashboard")

    def test_aislamiento_datos_bajo_carga(self):
        """Cada usuario solo ve sus propios registros aunque haya muchos en BD."""
        usuarios = []
        for i in range(5):
            u = Usuario.objects.create_user(
                correo=f'aislado{i}@stress.com',
                nombre=f'Aislado{i}', apellido='Test',
                password='Pass1234!'
            )
            u.email_verificado = True
            u.save(update_fields=['email_verificado'])
            datos_base(u)
            datos_base(u)
            usuarios.append(u)

        for u in usuarios:
            c = Client()
            c.force_login(u)
            r = c.get(reverse('clinico:historial'))
            registros = list(r.context['registros'])
            self.assertEqual(len(registros), 2,
                             f"Usuario {u.correo} vio {len(registros)} registros en lugar de 2")
            for reg in registros:
                self.assertEqual(reg.paciente, u,
                                 "Se filtraron registros ajenos bajo carga")
