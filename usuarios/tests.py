from django.test import TestCase, Client
from django.urls import reverse
from usuarios.models import Usuario


def crear_paciente(correo='test@test.com', password='Pass1234!'):
    return Usuario.objects.create_user(
        correo=correo, nombre='Ana', apellido='López', password=password
    )


def crear_admin(correo='admin@test.com', password='Admin1234!'):
    return Usuario.objects.create_superuser(
        correo=correo, nombre='Carlos', apellido='Admin', password=password
    )


# ─────────────────────────────────────────────
# MODELO Usuario
# ─────────────────────────────────────────────
class UsuarioModelTest(TestCase):

    def test_create_user_sets_fields_correctly(self):
        u = crear_paciente()
        self.assertEqual(u.correo, 'test@test.com')
        self.assertEqual(u.nombre, 'Ana')
        self.assertEqual(u.apellido, 'López')
        self.assertEqual(u.rol, 'paciente')
        self.assertTrue(u.activo)
        self.assertFalse(u.is_staff)
        self.assertFalse(u.bloqueado)
        self.assertEqual(u.intentos_fallidos, 0)

    def test_create_user_email_is_normalized(self):
        u = Usuario.objects.create_user(
            correo='TEST@EXAMPLE.COM', nombre='X', apellido='Y', password='pw'
        )
        self.assertEqual(u.correo, 'test@example.com')

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            Usuario.objects.create_user(
                correo='', nombre='X', apellido='Y', password='pw'
            )

    def test_create_superuser_is_staff_and_admin(self):
        a = crear_admin()
        self.assertTrue(a.is_staff)
        self.assertTrue(a.is_superuser)
        self.assertEqual(a.rol, 'administrador')

    def test_str_representation(self):
        u = crear_paciente()
        self.assertIn('Ana', str(u))
        self.assertIn('test@test.com', str(u))

    def test_password_is_hashed(self):
        u = crear_paciente()
        self.assertNotEqual(u.password, 'Pass1234!')
        self.assertTrue(u.check_password('Pass1234!'))

    def test_duplicate_email_raises_integrity_error(self):
        crear_paciente()
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            crear_paciente()  # mismo correo → debe fallar

    def test_rol_default_es_paciente(self):
        u = Usuario.objects.create_user(
            correo='nuevo@test.com', nombre='X', apellido='Y', password='pw'
        )
        self.assertEqual(u.rol, 'paciente')


# ─────────────────────────────────────────────
# VISTAS – Login / Logout / Registro
# ─────────────────────────────────────────────
class AuthViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = crear_paciente()

    def test_login_page_renders(self):
        r = self.client.get(reverse('usuarios:login'))
        self.assertEqual(r.status_code, 200)

    def test_login_post_valid_credentials_redirects(self):
        r = self.client.post(reverse('usuarios:login'), {
            'correo': 'test@test.com', 'password': 'Pass1234!'
        })
        self.assertRedirects(r, reverse('usuarios:dashboard'),
                             fetch_redirect_response=False)

    def test_login_post_wrong_password_stays_on_login(self):
        r = self.client.post(reverse('usuarios:login'), {
            'correo': 'test@test.com', 'password': 'wrongpassword'
        })
        self.assertEqual(r.status_code, 200)

    def test_login_post_nonexistent_user(self):
        r = self.client.post(reverse('usuarios:login'), {
            'correo': 'noexiste@test.com', 'password': 'Pass1234!'
        })
        self.assertEqual(r.status_code, 200)

    def test_logout_redirects_to_login(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse('usuarios:logout'))
        self.assertRedirects(r, reverse('usuarios:login'),
                             fetch_redirect_response=False)

    def test_registro_page_renders(self):
        r = self.client.get(reverse('usuarios:registro'))
        self.assertEqual(r.status_code, 200)


# ─────────────────────────────────────────────
# VISTA – Dashboard
# ─────────────────────────────────────────────
class DashboardViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.paciente = crear_paciente()
        self.admin = crear_admin()

    def test_dashboard_requires_login(self):
        r = self.client.get(reverse('usuarios:dashboard'))
        self.assertNotEqual(r.status_code, 200)

    def test_dashboard_patient_sees_patient_view(self):
        self.client.force_login(self.paciente)
        r = self.client.get(reverse('usuarios:dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context.get('es_admin', False))

    def test_dashboard_admin_sees_admin_view(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('usuarios:dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context.get('es_admin', False))

    def test_dashboard_patient_context_keys(self):
        self.client.force_login(self.paciente)
        r = self.client.get(reverse('usuarios:dashboard'))
        for key in ('total_registros', 'alertas_no_leidas',
                    'ultimo_registro', 'ultima_prediccion'):
            self.assertIn(key, r.context, msg=f"Falta clave '{key}' en context paciente")

    def test_dashboard_admin_context_keys(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('usuarios:dashboard'))
        for key in ('total_pacientes', 'total_registros',
                    'total_predicciones', 'alertas_pendientes'):
            self.assertIn(key, r.context, msg=f"Falta clave '{key}' en context admin")
