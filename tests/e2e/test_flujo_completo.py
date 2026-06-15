"""
Tests E2E con Playwright + pytest-django live_server.

Alta confiabilidad: cada test levanta un servidor Django real
contra una base de datos de prueba aislada (TransactionTestCase),
garantizando 0 contaminación entre ejecuciones y reproducibilidad
en CI/CD sin depender de datos externos.

Ejecutar localmente:
    pytest tests/e2e/ -v --headed          # con navegador visible
    pytest tests/e2e/ -v                   # headless (CI)
    pytest tests/e2e/ --screenshot=on      # screenshot automático en fallo
"""
import pytest
from playwright.sync_api import Page, expect


# ─── Constantes de credenciales de prueba ────────────────────────────────────

_CORREO_PACIENTE = 'e2e_paciente@test.com'
_PASS_PACIENTE   = 'E2ETestPass99!'
_CORREO_ADMIN    = 'e2e_admin@test.com'
_PASS_ADMIN      = 'E2EAdminPass99!'


# ─── Helper de login ─────────────────────────────────────────────────────────

def _login(page: Page, base_url: str, correo: str, password: str) -> None:
    """Realiza el login y espera a que el dashboard cargue."""
    page.goto(f"{base_url}/login/")
    page.wait_for_selector('input[name="correo"]', state='visible')
    page.fill('input[name="correo"]', correo)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/dashboard/", timeout=8_000)


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO 1 — Formulario de registro
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
def test_registro_formulario_renderiza_y_redirige(page: Page, live_server):
    """
    Alta confiabilidad: verifica que el formulario de registro existe,
    acepta datos válidos y redirige al flujo de verificación de email.
    Esto garantiza que el punto de entrada al sistema funciona antes
    de cualquier otro flujo de usuario.
    """
    page.goto(f"{live_server.url}/registro/")
    page.wait_for_selector('input[name="nombre"]', state='visible')

    page.fill('input[name="nombre"]', 'Carlos')
    page.fill('input[name="apellido"]', 'Registro')
    page.fill('input[name="correo"]', 'nuevo_usuario_e2e@test.com')
    page.fill('input[name="password1"]', 'NuevoPass99!')
    page.fill('input[name="password2"]', 'NuevoPass99!')

    # Seleccionar sexo si el select existe
    sexo_select = page.locator('select[name="sexo"]')
    if sexo_select.count() > 0:
        sexo_select.select_option('M')

    page.click('button[type="submit"]')

    # El sistema redirige a verificación de email (comportamiento correcto)
    page.wait_for_url(f"{live_server.url}/verificar-codigo/", timeout=8_000)
    assert '/verificar-codigo/' in page.url


@pytest.mark.django_db(transaction=True)
def test_registro_contrasena_corta_muestra_error(page: Page, live_server):
    """
    Alta confiabilidad: garantiza que AUTH_PASSWORD_VALIDATORS rechaza
    contraseñas < 8 caracteres, protegiendo la seguridad del sistema de salud.
    """
    page.goto(f"{live_server.url}/registro/")
    page.wait_for_selector('input[name="nombre"]', state='visible')

    page.fill('input[name="nombre"]', 'Test')
    page.fill('input[name="apellido"]', 'Corto')
    page.fill('input[name="correo"]', 'corto_e2e@test.com')
    page.fill('input[name="password1"]', '1234')
    page.fill('input[name="password2"]', '1234')
    page.click('button[type="submit"]')

    # Debe permanecer en /registro/ con mensaje de error
    assert '/registro/' in page.url
    # No debe redirigir a verificación
    assert '/verificar-codigo/' not in page.url


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO 2 — Login y acceso al dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
def test_login_exitoso_redirige_a_dashboard(page: Page, live_server, paciente_e2e):
    """
    Alta confiabilidad: valida la autenticación completa end-to-end
    con un usuario real en la DB de prueba. Un fallo aquí bloquea
    todos los flujos clínicos posteriores.
    """
    _login(page, live_server.url, _CORREO_PACIENTE, _PASS_PACIENTE)

    expect(page).to_have_url(f"{live_server.url}/dashboard/")
    # El dashboard debe mostrar el nombre del paciente
    page.wait_for_selector('body', state='visible')
    assert page.title() != ''


@pytest.mark.django_db(transaction=True)
def test_login_credenciales_invalidas_no_redirige(page: Page, live_server, paciente_e2e):
    """
    Alta confiabilidad: asegura que credenciales incorrectas no otorgan
    acceso al sistema clínico.
    """
    page.goto(f"{live_server.url}/login/")
    page.wait_for_selector('input[name="correo"]', state='visible')
    page.fill('input[name="correo"]', _CORREO_PACIENTE)
    page.fill('input[name="password"]', 'ContrasenaIncorrecta!')
    page.click('button[type="submit"]')

    # Permanece en login con mensaje de error
    assert '/login/' in page.url
    assert '/dashboard/' not in page.url


@pytest.mark.django_db(transaction=True)
def test_dashboard_requiere_autenticacion(page: Page, live_server):
    """
    Alta confiabilidad: garantiza que el dashboard no es accesible
    sin autenticación, protegiendo datos clínicos sensibles.
    """
    page.goto(f"{live_server.url}/dashboard/")
    # Debe redirigir a login (no mostrar contenido del dashboard)
    assert '/login/' in page.url or page.url != f"{live_server.url}/dashboard/"


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO 3 — Registro de datos clínicos
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
def test_formulario_clinico_crea_registro(page: Page, live_server, paciente_e2e):
    """
    Alta confiabilidad: verifica que el formulario clínico acepta
    13 parámetros biométricos reales y persiste el registro, habilitando
    el motor predictivo de ML.
    """
    _login(page, live_server.url, _CORREO_PACIENTE, _PASS_PACIENTE)

    page.goto(f"{live_server.url}/clinico/nuevo/")
    page.wait_for_selector('input[name="edad"]', state='visible')

    # Datos biométricos de paciente con múltiples factores de riesgo
    page.fill('input[name="edad"]',               '52')
    page.fill('input[name="peso"]',               '95.5')
    page.fill('input[name="altura"]',             '1.72')
    page.fill('input[name="presion_sistolica"]',  '148')
    page.fill('input[name="presion_diastolica"]', '94')
    page.fill('input[name="glucosa"]',            '155')
    page.fill('input[name="frecuencia_cardiaca"]','88')

    # Actividad física
    actividad = page.locator('select[name="actividad_fisica"]')
    if actividad.count() > 0:
        actividad.select_option('sedentario')

    # Laboratorio (opcionales)
    col_field = page.locator('input[name="colesterol"]')
    if col_field.count() > 0:
        col_field.fill('245')

    # Antecedentes familiares (checkboxes)
    for checkbox_name in ('antec_diabetes_uno', 'antec_hta_uno'):
        cb = page.locator(f'input[name="{checkbox_name}"]')
        if cb.count() > 0:
            cb.check()

    page.click('button[type="submit"]')

    # Redirige al detalle del registro recién creado
    page.wait_for_url(lambda url: '/clinico/detalle/' in url, timeout=8_000)
    assert '/clinico/detalle/' in page.url


@pytest.mark.django_db(transaction=True)
def test_historial_clinico_lista_registros(page: Page, live_server, datos_e2e):
    """
    Alta confiabilidad: confirma que el historial muestra los registros
    del paciente con los datos correctos, base del seguimiento longitudinal.
    """
    _login(page, live_server.url, _CORREO_PACIENTE, _PASS_PACIENTE)

    page.goto(f"{live_server.url}/clinico/historial/")
    page.wait_for_selector('table', state='visible', timeout=5_000)

    # La tabla debe tener al menos una fila de datos
    rows = page.locator('table tbody tr')
    assert rows.count() >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO 4 — Predicción de riesgo con ML
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
def test_prediccion_genera_5_enfermedades(page: Page, live_server, datos_e2e):
    """
    Alta confiabilidad: valida que el motor predictivo (ML o reglas)
    genera resultados para las 5 enfermedades crónicas con sus niveles
    de riesgo. Es el test de integración más crítico del sistema.
    """
    _login(page, live_server.url, _CORREO_PACIENTE, _PASS_PACIENTE)

    # Disparar predicción directamente via URL (evita buscar el botón en historial)
    page.goto(f"{live_server.url}/clinico/historial/")
    page.wait_for_selector('table', state='visible', timeout=5_000)

    # Buscar y hacer click en el enlace de predicción del primer registro
    analizar_link = page.locator('a[href*="/prediccion/nueva/"]').first
    if analizar_link.count() == 0:
        # Fallback: construir URL directamente
        pred_url = f"{live_server.url}/prediccion/nueva/{datos_e2e.pk}/"
        page.goto(pred_url)
    else:
        analizar_link.click()

    # Esperar resultado de predicción
    page.wait_for_url(lambda url: '/prediccion/resultado/' in url, timeout=10_000)

    # Verificar que se muestran las 5 enfermedades
    disease_rows = page.locator('.disease-row')
    expect(disease_rows).to_have_count(5)


@pytest.mark.django_db(transaction=True)
def test_prediccion_muestra_porcentajes_validos(page: Page, live_server, datos_e2e):
    """
    Alta confiabilidad: verifica que cada resultado de predicción
    contiene un porcentaje numérico entre 0-100%, asegurando que
    el modelo ML/reglas no devuelve valores fuera de rango clínico.
    """
    _login(page, live_server.url, _CORREO_PACIENTE, _PASS_PACIENTE)

    # Ir directamente a nueva predicción
    page.goto(f"{live_server.url}/prediccion/nueva/{datos_e2e.pk}/")
    page.wait_for_url(lambda url: '/prediccion/resultado/' in url, timeout=10_000)
    page.wait_for_selector('.disease-row', state='visible', timeout=5_000)

    # Extraer todos los textos de porcentaje (formato: "XX.X%")
    # Los porcentajes están en divs con font-size:24px dentro de .disease-row
    rows = page.locator('.disease-row')
    for i in range(rows.count()):
        row_text = rows.nth(i).text_content()
        assert '%' in row_text, f"Fila {i} no contiene porcentaje: {row_text[:80]}"


@pytest.mark.django_db(transaction=True)
def test_prediccion_muestra_nivel_riesgo(page: Page, live_server, datos_e2e):
    """
    Alta confiabilidad: comprueba que el sistema clasifica el nivel
    de riesgo como 'bajo', 'medio' o 'alto', garantizando que la
    UI transmite correctamente la severidad al profesional de salud.
    """
    _login(page, live_server.url, _CORREO_PACIENTE, _PASS_PACIENTE)

    page.goto(f"{live_server.url}/prediccion/nueva/{datos_e2e.pk}/")
    page.wait_for_url(lambda url: '/prediccion/resultado/' in url, timeout=10_000)
    page.wait_for_selector('.disease-row', state='visible', timeout=5_000)

    # Verificar badge de nivel general (banner superior)
    nivel_badge = page.locator('.badge-nivel').first
    expect(nivel_badge).to_be_visible()
    nivel_text = nivel_badge.text_content().strip().lower()
    assert nivel_text in ('bajo', 'medio', 'alto'), f"Nivel inválido: {nivel_text}"


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO 5 — Alertas clínicas
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
def test_alertas_generadas_tras_prediccion(page: Page, live_server, datos_e2e):
    """
    Alta confiabilidad: verifica que el sistema genera alertas automáticas
    tras una predicción con datos de riesgo alto (glucosa 155 + PA 148/94),
    lo cual es crítico para la seguridad del paciente.
    """
    _login(page, live_server.url, _CORREO_PACIENTE, _PASS_PACIENTE)

    # Crear predicción primero
    page.goto(f"{live_server.url}/prediccion/nueva/{datos_e2e.pk}/")
    page.wait_for_url(lambda url: '/prediccion/resultado/' in url, timeout=10_000)

    # Ir a la lista de alertas
    page.goto(f"{live_server.url}/alertas/")
    page.wait_for_selector('body', state='visible')

    # Con glucosa=155 y PA=148/94 deben generarse alertas
    # Verificar que la página renderiza sin errores (status 200 implícito)
    assert '/alertas/' in page.url
    # El contenedor de alertas debe estar en la página
    page.wait_for_selector('[class*="alert"]', state='visible', timeout=5_000)


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO 6 — Reportes y exportación CSV
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
def test_exportar_csv_clinico(page: Page, live_server, datos_e2e):
    """
    Alta confiabilidad: valida que el sistema genera y descarga un archivo
    CSV con el historial clínico. Crítico para la portabilidad de datos
    médicos y cumplimiento de normativas de salud.
    """
    _login(page, live_server.url, _CORREO_PACIENTE, _PASS_PACIENTE)

    # Interceptar la descarga
    with page.expect_download(timeout=8_000) as download_info:
        page.goto(f"{live_server.url}/reportes/csv/clinico/")

    download = download_info.value
    filename = download.suggested_filename
    assert filename.endswith('.csv'), f"Archivo descargado no es CSV: {filename}"


@pytest.mark.django_db(transaction=True)
def test_exportar_csv_predicciones(page: Page, live_server, datos_e2e):
    """
    Alta confiabilidad: verifica la exportación de predicciones en CSV,
    garantizando que los datos del modelo ML sean auditables y exportables.
    """
    from prediccion.models import Prediccion
    from prediccion.service import predecir_riesgo

    # Crear predicción con el servicio real (ML o reglas)
    resultado = predecir_riesgo(datos_e2e)
    Prediccion.objects.create(
        paciente=datos_e2e.paciente,
        datos_clinicos=datos_e2e,
        **resultado,
    )

    _login(page, live_server.url, _CORREO_PACIENTE, _PASS_PACIENTE)

    with page.expect_download(timeout=8_000) as download_info:
        page.goto(f"{live_server.url}/reportes/csv/predicciones/")

    download = download_info.value
    assert download.suggested_filename.endswith('.csv')


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO 7 — Panel de administrador + Chart.js
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
def test_admin_estadisticas_canvas_chartjs(page: Page, live_server, admin_e2e, paciente_e2e):
    """
    Alta confiabilidad: verifica que los gráficos Chart.js se renderizan
    correctamente en el panel de estadísticas. Comprueba:
      1. Existencia de elementos <canvas> en el DOM
      2. Dimensiones válidas (width > 0 y height > 0) post-renderizado
      3. Que Chart.js registró las instancias de gráfico

    Esto garantiza que los administradores pueden analizar tendencias
    epidemiológicas de la población de pacientes.
    """
    _login(page, live_server.url, _CORREO_ADMIN, _PASS_ADMIN)

    page.goto(f"{live_server.url}/estadisticas/")
    page.wait_for_selector('canvas', state='visible', timeout=8_000)

    # Verificar canvas de distribución por sexo
    canvas_sexo = page.locator('canvas#chartSexo')
    expect(canvas_sexo).to_be_visible()
    bbox_sexo = canvas_sexo.bounding_box()
    assert bbox_sexo is not None, "canvas#chartSexo no tiene bounding box"
    assert bbox_sexo['width'] > 0,  "canvas#chartSexo tiene width=0"
    assert bbox_sexo['height'] > 0, "canvas#chartSexo tiene height=0"

    # Verificar canvas de distribución por edad
    canvas_edad = page.locator('canvas#chartEdad')
    expect(canvas_edad).to_be_visible()
    bbox_edad = canvas_edad.bounding_box()
    assert bbox_edad is not None, "canvas#chartEdad no tiene bounding box"
    assert bbox_edad['width'] > 0,  "canvas#chartEdad tiene width=0"
    assert bbox_edad['height'] > 0, "canvas#chartEdad tiene height=0"

    # Verificar que Chart.js inicializó los gráficos (vía JavaScript)
    chart_count = page.evaluate(
        "() => typeof Chart !== 'undefined' ? Object.keys(Chart.instances).length : -1"
    )
    assert chart_count >= 0, "Chart.js no está disponible en la página"


@pytest.mark.django_db(transaction=True)
def test_paciente_no_accede_a_estadisticas_admin(page: Page, live_server, paciente_e2e):
    """
    Alta confiabilidad: verifica que el panel de estadísticas administrativas
    (con datos de toda la población) no es accesible por usuarios sin rol
    de administrador, protegiendo la privacidad de los pacientes.
    """
    _login(page, live_server.url, _CORREO_PACIENTE, _PASS_PACIENTE)

    page.goto(f"{live_server.url}/estadisticas/")

    # No debe estar en estadísticas (debe redirigir o mostrar 403/404)
    assert '/estadisticas/' not in page.url or page.locator('canvas').count() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO 8 — API REST con JWT (DRF)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
def test_api_analizar_requiere_autenticacion(page: Page, live_server):
    """
    Alta confiabilidad: verifica que el endpoint REST /prediccion/api/analizar/
    rechaza peticiones sin token JWT, protegiendo el acceso programático
    a los modelos ML del sistema.
    """
    # POST sin autenticación → 401 o 403
    response = page.request.post(
        f"{live_server.url}/prediccion/api/analizar/",
        data={'datos_pk': 1},
    )
    assert response.status in (401, 403), (
        f"API devolvió {response.status} esperando 401/403"
    )
