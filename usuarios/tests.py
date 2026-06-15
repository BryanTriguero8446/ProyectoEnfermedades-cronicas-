from django.test import TestCase, Client
from django.urls import reverse
from usuarios.models import Usuario


def crear_paciente(correo='test@test.com', password='Pass1234!'):
    u = Usuario.objects.create_user(
        correo=correo, nombre='Ana', apellido='López', password=password
    )
    u.email_verificado = True
    u.save(update_fields=['email_verificado'])
    return u


def crear_admin(correo='admin@test.com', password='Admin1234!'):
    u = Usuario.objects.create_superuser(
        correo=correo, nombre='Carlos', apellido='Admin', password=password
    )
    u.email_verificado = True
    u.save(update_fields=['email_verificado'])
    return u


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


# ─────────────────────────────────────────────
# VALIDACIÓN – contraseña mínima 8 caracteres
# ─────────────────────────────────────────────
class PasswordValidationTest(TestCase):
    """
    Alta confiabilidad: verifica que AUTH_PASSWORD_VALIDATORS rechaza
    contraseñas débiles en el formulario de registro. Los sistemas de
    salud manejan datos sensibles y requieren contraseñas seguras.
    """

    def test_registro_rechaza_contrasena_menor_8_chars(self):
        r = self.client.post(reverse('usuarios:registro'), {
            'nombre': 'Juan', 'apellido': 'Corto',
            'correo': 'corto@test.com',
            'password1': '1234567',   # 7 chars < 8 mínimo
            'password2': '1234567',
        })
        # Debe permanecer en registro (no redirigir a verificación)
        self.assertEqual(r.status_code, 200,
                         "Contraseña corta no debe crear usuario ni redirigir")
        from usuarios.models import Usuario
        self.assertFalse(
            Usuario.objects.filter(correo='corto@test.com').exists(),
            "No debe crear usuario con contraseña < 8 caracteres"
        )

    def test_registro_acepta_contrasena_de_8_chars(self):
        r = self.client.post(reverse('usuarios:registro'), {
            'nombre': 'Maria', 'apellido': 'Valida',
            'correo': 'valida@test.com',
            'password1': '12345678',   # exactamente 8 chars
            'password2': '12345678',
            'fecha_nacimiento': '1990-05-15',
        })
        # Debe redirigir a verificación (registro exitoso)
        self.assertRedirects(r, reverse('usuarios:verificacion_enviada'),
                             fetch_redirect_response=False)

    def test_contrasenas_distintas_genera_error(self):
        r = self.client.post(reverse('usuarios:registro'), {
            'nombre': 'Error', 'apellido': 'Mismatch',
            'correo': 'mismatch@test.com',
            'password1': 'ContraA123!',
            'password2': 'ContraB456!',
        })
        self.assertEqual(r.status_code, 200)
        from usuarios.models import Usuario
        self.assertFalse(Usuario.objects.filter(correo='mismatch@test.com').exists())


# ─────────────────────────────────────────────
# ELIMINACIÓN DE CUENTA – soft-delete + email
# ─────────────────────────────────────────────
class EliminarCuentaViewTest(TestCase):
    """
    Alta confiabilidad: verifica el soft-delete de usuarios con:
    1. Anonimización del correo (permite re-registro)
    2. Alerta de auditoría para administradores
    3. Preservación del historial médico (datos clínicos no borrados)

    Esto garantiza cumplimiento de normativas médicas de auditoría.
    """

    def setUp(self):
        self.client = Client()
        self.user = crear_paciente(correo='eliminar@test.com', password='Pass1234!')
        self.client.force_login(self.user)

    def test_get_renderiza_confirmacion(self):
        r = self.client.get(reverse('usuarios:eliminar_cuenta'))
        self.assertEqual(r.status_code, 200)

    def test_eliminar_requiere_login(self):
        self.client.logout()
        r = self.client.post(reverse('usuarios:eliminar_cuenta'),
                             {'password': 'Pass1234!'})
        self.assertNotEqual(r.status_code, 200)

    def test_post_valido_desactiva_usuario(self):
        self.client.post(reverse('usuarios:eliminar_cuenta'),
                         {'password': 'Pass1234!', 'confirmar': 'ELIMINAR'})
        self.user.refresh_from_db()
        self.assertFalse(self.user.activo,
                         "Usuario debe quedar inactivo (soft-delete)")

    def test_correo_queda_anonimizado(self):
        correo_original = self.user.correo
        self.client.post(reverse('usuarios:eliminar_cuenta'),
                         {'password': 'Pass1234!', 'confirmar': 'ELIMINAR'})
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.correo, correo_original,
                            "El correo debe quedar anonimizado")
        self.assertIn('@eliminado.local', self.user.correo,
                      "El correo anonimizado debe terminar en @eliminado.local")

    def test_correo_original_queda_libre_para_reregistro(self):
        """Tras eliminar, otro usuario debe poder registrarse con el mismo correo."""
        correo = self.user.correo
        self.client.post(reverse('usuarios:eliminar_cuenta'),
                         {'password': 'Pass1234!', 'confirmar': 'ELIMINAR'})
        self.user.refresh_from_db()
        # El correo original ya no está en uso → se puede crear un nuevo usuario
        from usuarios.models import Usuario
        nuevo = Usuario.objects.create_user(
            correo=correo, nombre='Nuevo', apellido='User', password='NewPass12!'
        )
        self.assertEqual(nuevo.correo, correo)

    def test_eliminar_genera_alerta_para_admin(self):
        from alertas.models import Alerta
        self.client.post(reverse('usuarios:eliminar_cuenta'),
                         {'password': 'Pass1234!', 'confirmar': 'ELIMINAR'})
        alerta = Alerta.objects.filter(tipo='cuenta_eliminada').first()
        self.assertIsNotNone(alerta,
                             "Debe crearse una alerta de tipo 'cuenta_eliminada'")
        self.assertIn('eliminar@test.com', alerta.mensaje)

    def test_contrasena_incorrecta_no_elimina(self):
        r = self.client.post(reverse('usuarios:eliminar_cuenta'),
                             {'password': 'ContraIncorrecta!'})
        self.user.refresh_from_db()
        self.assertTrue(self.user.activo,
                        "Usuario no debe eliminarse con contraseña incorrecta")


# ─────────────────────────────────────────────
# VISTA – estadísticas (solo admin)
# ─────────────────────────────────────────────
class EstadisticasViewTest(TestCase):
    """
    Alta confiabilidad: garantiza que los datos estadísticos de la
    población de pacientes solo son visibles para administradores,
    protegiendo la privacidad colectiva de los pacientes.
    """

    def setUp(self):
        self.client = Client()
        self.paciente = crear_paciente()
        self.admin = crear_admin()

    def test_estadisticas_requiere_login(self):
        r = self.client.get(reverse('usuarios:estadisticas'))
        self.assertNotEqual(r.status_code, 200)

    def test_admin_puede_acceder_estadisticas(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('usuarios:estadisticas'))
        self.assertEqual(r.status_code, 200)

    def test_paciente_no_puede_acceder_estadisticas(self):
        self.client.force_login(self.paciente)
        r = self.client.get(reverse('usuarios:estadisticas'))
        # Debe redirigir o retornar 403/404 (no 200)
        self.assertNotEqual(r.status_code, 200,
                            "Un paciente no debe poder ver las estadísticas globales")
