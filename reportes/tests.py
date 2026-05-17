import csv
import io
from django.test import TestCase, Client
from django.urls import reverse
from usuarios.models import Usuario
from clinico.models import DatosClinico
from prediccion.models import Prediccion
from reportes.models import Reporte


def crear_usuario(correo='rep@test.com'):
    return Usuario.objects.create_user(
        correo=correo, nombre='Luis', apellido='Test', password='Pass1234!'
    )


def datos_base(paciente, **kwargs):
    defaults = dict(
        paciente=paciente,
        edad=40, peso=75.0, altura=1.72,
        presion_sistolica=118, presion_diastolica=76,
        glucosa=92.0, frecuencia_cardiaca=68,
        actividad_fisica='moderado',
    )
    defaults.update(kwargs)
    d = DatosClinico(**defaults)
    d.save()
    return d


HEADERS_CSV_CLINICO = [
    'Fecha', 'Edad', 'Peso (kg)', 'Altura (m)', 'IMC',
    'Presión Sistólica', 'Presión Diastólica',
    'Glucosa (mg/dL)', 'Frecuencia Cardíaca',
    'Colesterol', 'Triglicéridos', 'Creatinina',
    'Actividad Física', 'Fumador', 'Alcohol', 'Observaciones',
]

HEADERS_CSV_PREDICCIONES = [
    'Fecha', 'Versión Modelo',
    '% Diabetes', 'Nivel Diabetes',
    '% Hipertensión', 'Nivel Hipertensión',
    '% Renal', 'Nivel Renal',
    '% NAFLD', 'Nivel NAFLD',
    '% Cardíaco', 'Nivel Cardíaco',
    'Nivel General',
]


# ─────────────────────────────────────────────
# CSV Clínico
# ─────────────────────────────────────────────
class CSVClinicoTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = crear_usuario()
        self.client.force_login(self.user)
        self.datos = datos_base(self.user, glucosa=95.0, edad=40)

    def test_requiere_login(self):
        self.client.logout()
        r = self.client.get(reverse('reportes:csv_clinico'))
        self.assertNotEqual(r.status_code, 200)

    def test_respuesta_es_csv(self):
        r = self.client.get(reverse('reportes:csv_clinico'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/csv', r['Content-Type'])

    def test_content_disposition_attachment(self):
        r = self.client.get(reverse('reportes:csv_clinico'))
        self.assertIn('attachment', r['Content-Disposition'])
        self.assertIn('.csv', r['Content-Disposition'])

    def test_cabeceras_correctas(self):
        r = self.client.get(reverse('reportes:csv_clinico'))
        # Decodificar ignorando BOM
        content = r.content.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(content))
        headers = next(reader)
        self.assertEqual(headers, HEADERS_CSV_CLINICO)

    def test_contiene_datos_del_paciente(self):
        r = self.client.get(reverse('reportes:csv_clinico'))
        content = r.content.decode('utf-8-sig')
        self.assertIn('95', content)   # glucosa
        self.assertIn('40', content)   # edad

    def test_no_contiene_datos_de_otros_pacientes(self):
        otro = crear_usuario('otro@rep.com')
        datos_base(otro, glucosa=999.0)
        r = self.client.get(reverse('reportes:csv_clinico'))
        content = r.content.decode('utf-8-sig')
        self.assertNotIn('999', content)

    def test_crea_registro_reporte_en_bd(self):
        count_antes = Reporte.objects.count()
        self.client.get(reverse('reportes:csv_clinico'))
        self.assertEqual(Reporte.objects.count(), count_antes + 1)

    def test_reporte_guardado_con_estado_listo(self):
        self.client.get(reverse('reportes:csv_clinico'))
        rep = Reporte.objects.latest('fecha_generacion')
        self.assertEqual(rep.estado, 'listo')
        self.assertEqual(rep.formato, 'csv')
        self.assertEqual(rep.tipo, 'clinico')

    def test_fumador_aparece_como_si_o_no(self):
        datos_base(self.user, fumador=True)
        r = self.client.get(reverse('reportes:csv_clinico'))
        content = r.content.decode('utf-8-sig')
        self.assertIn('Sí', content)

    def test_csv_sin_registros_solo_cabecera(self):
        DatosClinico.objects.filter(paciente=self.user).delete()
        r = self.client.get(reverse('reportes:csv_clinico'))
        content = r.content.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(content))
        filas = list(reader)
        # Solo la fila de headers, sin datos
        self.assertEqual(len(filas), 1)


# ─────────────────────────────────────────────
# CSV Predicciones
# ─────────────────────────────────────────────
class CSVPrediccionesTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = crear_usuario()
        self.client.force_login(self.user)
        datos = datos_base(self.user)
        self.pred = Prediccion.objects.create(
            paciente=self.user,
            datos_clinicos=datos,
            riesgo_diabetes=25, nivel_diabetes='bajo',
            riesgo_hipertension=15, nivel_hipertension='bajo',
            riesgo_renal=10, nivel_renal='bajo',
            riesgo_nafld=8, nivel_nafld='bajo',
            riesgo_cardiaco=12, nivel_cardiaco='bajo',
            modelo_version='rule_based_v1',
        )

    def test_requiere_login(self):
        self.client.logout()
        r = self.client.get(reverse('reportes:csv_predicciones'))
        self.assertNotEqual(r.status_code, 200)

    def test_respuesta_es_csv(self):
        r = self.client.get(reverse('reportes:csv_predicciones'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/csv', r['Content-Type'])

    def test_cabeceras_predicciones_correctas(self):
        r = self.client.get(reverse('reportes:csv_predicciones'))
        content = r.content.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(content))
        headers = next(reader)
        self.assertEqual(headers, HEADERS_CSV_PREDICCIONES)

    def test_contiene_datos_de_prediccion(self):
        r = self.client.get(reverse('reportes:csv_predicciones'))
        content = r.content.decode('utf-8-sig')
        self.assertIn('rule_based_v1', content)
        self.assertIn('25', content)   # riesgo_diabetes

    def test_crea_registro_reporte_prediccion(self):
        count_antes = Reporte.objects.count()
        self.client.get(reverse('reportes:csv_predicciones'))
        self.assertEqual(Reporte.objects.count(), count_antes + 1)
        rep = Reporte.objects.latest('fecha_generacion')
        self.assertEqual(rep.tipo, 'prediccion')


# ─────────────────────────────────────────────
# VISTA – lista_reportes
# ─────────────────────────────────────────────
class ListaReportesViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = crear_usuario()
        self.client.force_login(self.user)

    def test_lista_requiere_login(self):
        self.client.logout()
        r = self.client.get(reverse('reportes:lista'))
        self.assertNotEqual(r.status_code, 200)

    def test_lista_renderiza(self):
        r = self.client.get(reverse('reportes:lista'))
        self.assertEqual(r.status_code, 200)

    def test_lista_no_muestra_reportes_ajenos(self):
        otro = crear_usuario('otro@rep2.com')
        datos = datos_base(otro)
        Reporte.objects.create(
            paciente=otro, formato='csv', tipo='clinico',
            estado='listo', generado_por=otro,
            parametros={},
        )
        r = self.client.get(reverse('reportes:lista'))
        reportes_ctx = list(r.context['reportes'])
        self.assertEqual(len(reportes_ctx), 0)
