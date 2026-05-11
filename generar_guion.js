const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
        BorderStyle, PageNumber, Header, Footer, LevelFormat, NumberFormat } = require('docx');
const fs = require('fs');

// ─── Colores ──────────────────────────────────────────────────────────────────
const AZUL     = "1F4E79";
const AZUL_MED = "2E75B6";
const GRIS     = "595959";
const NEGRO    = "000000";

// ─── Helpers ──────────────────────────────────────────────────────────────────
function titulo(texto) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 160 },
    children: [new TextRun({ text: texto, bold: true, color: AZUL, size: 32, font: "Arial" })]
  });
}
function subtitulo(texto) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 120 },
    children: [new TextRun({ text: texto, bold: true, color: AZUL_MED, size: 26, font: "Arial" })]
  });
}
function parrafo(texto, opts = {}) {
  return new Paragraph({
    spacing: { before: 80, after: 120 },
    children: [new TextRun({ text: texto, size: 22, font: "Arial", color: NEGRO, ...opts })]
  });
}
function codigo(texto) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    indent: { left: 720 },
    border: { left: { style: BorderStyle.SINGLE, size: 6, color: AZUL_MED, space: 10 } },
    children: [new TextRun({ text: texto, size: 20, font: "Courier New", color: "1a5276" })]
  });
}
function viñeta(texto) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text: texto, size: 22, font: "Arial", color: NEGRO })]
  });
}
function separador() {
  return new Paragraph({
    spacing: { before: 200, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "BDC3C7", space: 1 } },
    children: []
  });
}
function nota(texto) {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    indent: { left: 720 },
    children: [new TextRun({ text: "Nota: " + texto, size: 20, font: "Arial", color: "7F8C8D", italics: true })]
  });
}

// ─── Documento ────────────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{
        level: 0,
        format: LevelFormat.BULLET,
        text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    }]
  },
  styles: {
    default: {
      document: { run: { font: "Arial", size: 22, color: NEGRO } }
    }
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1260, bottom: 1440, left: 1260 }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: AZUL_MED, space: 1 } },
          children: [
            new TextRun({ text: "ClinicalLens  |  Guion del Proyecto", size: 18, font: "Arial", color: AZUL_MED }),
            new TextRun({ text: "   Bryan Triguero — UNIFRANZ 2025", size: 18, font: "Arial", color: GRIS })
          ]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: "BDC3C7", space: 1 } },
          children: [
            new TextRun({ text: "Pagina ", size: 18, font: "Arial", color: GRIS }),
            new TextRun({ children: [PageNumber.CURRENT], size: 18, font: "Arial", color: GRIS }),
            new TextRun({ text: " de ", size: 18, font: "Arial", color: GRIS }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, font: "Arial", color: GRIS }),
          ]
        })]
      })
    },
    children: [

      // ═══════════════════════════════════════════════════════ PORTADA
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 1440, after: 240 },
        children: [new TextRun({ text: "UNIVERSIDAD PRIVADA FRANZ TAMAYO", bold: true, size: 28, font: "Arial", color: AZUL, allCaps: true })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "Carrera de Ingenieria en Sistemas", size: 22, font: "Arial", color: GRIS })]
      }),
      separador(),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 480, after: 240 },
        children: [new TextRun({ text: "ClinicalLens", bold: true, size: 52, font: "Arial", color: AZUL_MED })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: "Sistema Web Predictivo de Salud", size: 28, font: "Arial", color: GRIS })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 600 },
        children: [new TextRun({ text: "Guion Tecnico — Construccion del Proyecto desde Cero", italics: true, size: 22, font: "Arial", color: GRIS })]
      }),
      separador(),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 480, after: 80 },
        children: [new TextRun({ text: "Autor:", bold: true, size: 22, font: "Arial", color: NEGRO })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "Bryan Triguero", bold: true, size: 26, font: "Arial", color: AZUL })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "Materia: Testing de Software  |  7mo Semestre", size: 22, font: "Arial", color: GRIS })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "Gestion: 2025", size: 22, font: "Arial", color: GRIS })]
      }),

      // ═══════════════════════════════════════════════════════ INTRO
      separador(),
      titulo("Introduccion"),
      parrafo(
        "Este documento es el relato tecnico de como construi ClinicalLens desde cero. " +
        "Describo cada decision, cada comando ejecutado y cada problema que resolvi durante el desarrollo. " +
        "El proyecto consiste en una aplicacion web de salud que predice el nivel de riesgo de un paciente " +
        "para cinco enfermedades: diabetes, hipertension, enfermedad renal, higado graso e insuficiencia cardiaca."
      ),
      parrafo(
        "Tecnologias utilizadas: Python 3.10, Django 5.2, Bootstrap 5.3, scikit-learn, " +
        "PostgreSQL (planificado) / SQLite (desarrollo). El repositorio esta en GitHub: " +
        "https://github.com/BryanTriguero8446/ClinicalLens"
      ),

      // ═══════════════════════════════════════════════════════ FASE 1
      separador(),
      titulo("Fase 1 — Creacion del entorno y estructura base"),

      subtitulo("1.1  Creacion de la carpeta del proyecto"),
      parrafo(
        "Lo primero que hice fue crear la carpeta principal del proyecto en mi computadora. " +
        "Decidi ubicarla dentro de la ruta de la universidad para mantener todo organizado."
      ),
      codigo("mkdir C:\\Users\\DELL\\Documents\\1.-Bryan\\UNIFRANZ\\7MO SEMESTRE\\TESTING\\clinical_lens"),
      codigo("cd clinical_lens"),

      subtitulo("1.2  Entorno virtual de Python"),
      parrafo(
        "Cree un entorno virtual para aislar las dependencias del proyecto y no mezclarlas " +
        "con otros proyectos de Python que tengo instalados en la misma maquina."
      ),
      codigo("python -m venv venv"),
      codigo("venv\\Scripts\\activate"),

      subtitulo("1.3  Instalacion de dependencias"),
      parrafo("Con el entorno activo instale todas las librerias que necesitaba:"),
      codigo("pip install django djangorestframework django-cors-headers"),
      parrafo("Luego genere el archivo de dependencias para que cualquiera pueda reproducir el entorno:"),
      codigo("pip freeze > requirements.txt"),

      subtitulo("1.4  Inicializacion del proyecto Django"),
      parrafo(
        "Cree el proyecto Django principal llamado 'config'. Este nombre es una convencion " +
        "que uso para que quede claro que esa carpeta contiene solo configuracion global."
      ),
      codigo("django-admin startproject config ."),
      parrafo(
        "El punto final '.' es importante: le indica a Django que cree el proyecto en la carpeta " +
        "actual en lugar de crear una subcarpeta adicional."
      ),

      subtitulo("1.5  Creacion de las aplicaciones Django"),
      parrafo(
        "Dividi la logica del sistema en cinco aplicaciones independientes, cada una con " +
        "responsabilidad unica (principio de responsabilidad unica):"
      ),
      codigo("python manage.py startapp usuarios"),
      codigo("python manage.py startapp clinico"),
      codigo("python manage.py startapp prediccion"),
      codigo("python manage.py startapp alertas"),
      codigo("python manage.py startapp reportes"),
      parrafo("Cada app contiene sus propios modelos, vistas, URLs y formularios."),

      subtitulo("1.6  Repositorio en GitHub"),
      parrafo("Inicialice Git y subi el proyecto a GitHub para tener control de versiones desde el inicio:"),
      codigo("git init"),
      codigo("git add ."),
      codigo("git commit -m \"feat: proyecto inicial ClinicalLens\""),
      codigo("git remote add origin https://github.com/BryanTriguero8446/ClinicalLens.git"),
      codigo("git push -u origin main"),

      // ═══════════════════════════════════════════════════════ FASE 2
      separador(),
      titulo("Fase 2 — Modelos de base de datos"),

      subtitulo("2.1  Modelo de usuario personalizado (usuarios/models.py)"),
      parrafo(
        "Django trae un modelo de usuario por defecto, pero no tenia el campo 'correo' como " +
        "identificador principal ni el campo 'rol' que necesitaba. Por eso cree un modelo " +
        "personalizado heredando de AbstractBaseUser."
      ),
      parrafo("Los campos principales del modelo Usuario son:"),
      viñeta("correo (EmailField, unico) — usado como nombre de usuario para login"),
      viñeta("nombre, apellido — datos personales del usuario"),
      viñeta("rol — 'paciente' o 'administrador'"),
      viñeta("activo — permite desactivar cuentas sin borrarlas"),
      parrafo(
        "En settings.py configure AUTH_USER_MODEL = 'usuarios.Usuario' para que Django " +
        "use mi modelo en lugar del suyo."
      ),

      subtitulo("2.2  Modelo de datos clinicos (clinico/models.py)"),
      parrafo(
        "Este modelo almacena las mediciones del paciente. Cada registro clinico esta " +
        "asociado a un usuario (paciente) mediante ForeignKey."
      ),
      parrafo("Campos del modelo DatosClinico:"),
      viñeta("paciente — FK a Usuario"),
      viñeta("edad, genero, peso, talla — datos basicos"),
      viñeta("glucosa, presion_sistolica, presion_diastolica — signos vitales"),
      viñeta("colesterol, imc — indicadores metabolicos calculados"),
      viñeta("fecha_registro — timestamp automatico"),

      subtitulo("2.3  Modelo de prediccion (prediccion/models.py)"),
      parrafo(
        "Almacena los resultados de cada analisis de riesgo. Cada prediccion esta ligada " +
        "a un registro clinico y al paciente."
      ),
      parrafo("Campos clave:"),
      viñeta("riesgo_diabetes, riesgo_hipertension, riesgo_renal, riesgo_nafld, riesgo_cardiaco — porcentaje 0-100"),
      viñeta("nivel_diabetes, nivel_hipertension, etc. — 'Bajo', 'Medio' o 'Alto'"),
      viñeta("nivel_general — nivel mas alto entre todas las enfermedades"),
      viñeta("fecha_prediccion — timestamp"),

      subtitulo("2.4  Migraciones"),
      parrafo("Aplique las migraciones para crear las tablas en la base de datos SQLite:"),
      codigo("python manage.py makemigrations"),
      codigo("python manage.py migrate"),

      // ═══════════════════════════════════════════════════════ FASE 3
      separador(),
      titulo("Fase 3 — Autenticacion y control de acceso"),

      subtitulo("3.1  Sistema de login personalizado"),
      parrafo(
        "Implemente el login usando el correo electronico como identificador (no el username " +
        "de Django). La vista login_view en usuarios/views.py busca al usuario por correo, " +
        "verifica la contrasena con check_password() y luego llama a login() de Django."
      ),

      subtitulo("3.2  Registro de accesos (HistorialAccesos)"),
      parrafo(
        "Cada vez que un usuario inicia o cierra sesion, el sistema registra la accion, " +
        "la IP del cliente y el timestamp. Esto sirve para auditar el uso del sistema. " +
        "Los eventos registrados son: login_ok, login_fail, logout."
      ),

      subtitulo("3.3  Proteccion de vistas"),
      parrafo(
        "Use el decorador @login_required en todas las vistas que requieren autenticacion. " +
        "Si un usuario no autenticado intenta acceder, es redirigido automaticamente al login."
      ),
      codigo("@login_required(login_url='usuarios:login')"),
      codigo("def dashboard_view(request):"),
      codigo("    ..."),

      subtitulo("3.4  Roles: paciente vs administrador"),
      parrafo(
        "El dashboard muestra contenido diferente segun el rol del usuario. " +
        "Los administradores ven estadisticas globales (total pacientes, total predicciones, " +
        "alertas pendientes). Los pacientes ven solo sus propios datos."
      ),

      // ═══════════════════════════════════════════════════════ FASE 4
      separador(),
      titulo("Fase 4 — Interfaz de usuario (templates)"),

      subtitulo("4.1  Estructura de templates"),
      parrafo(
        "Organice los templates en carpetas por aplicacion dentro de la carpeta 'templates/' " +
        "en la raiz del proyecto. En settings.py configure DIRS para que Django los encuentre."
      ),
      parrafo("La estructura de templates es la siguiente:"),
      viñeta("templates/base.html — layout principal con sidebar (solo usuarios autenticados)"),
      viñeta("templates/base_auth.html — layout minimo para login y registro"),
      viñeta("templates/auth/ — login.html, registro.html"),
      viñeta("templates/dashboard/ — index.html"),
      viñeta("templates/clinico/ — nuevo_registro.html, historial.html"),
      viñeta("templates/prediccion/ — historial.html, resultado.html"),
      viñeta("templates/alertas/ — lista.html"),
      viñeta("templates/reportes/ — reportes.html"),

      subtitulo("4.2  El problema del bloque duplicado en base.html"),
      parrafo(
        "Uno de los errores mas complejos que resolvi fue un TemplateSyntaxError que decia: " +
        "'block tag with name content appears more than once'. Habia intentado poner un " +
        "{% if user.is_authenticated %} dentro de base.html para mostrar el sidebar solo " +
        "a usuarios autenticados, pero Django compila los templates antes de ejecutarlos, " +
        "por lo que no puede tener dos bloques con el mismo nombre aunque esten en ramas " +
        "if/else diferentes."
      ),
      parrafo(
        "La solucion fue crear dos templates base separados: base.html (con sidebar, para " +
        "vistas autenticadas) y base_auth.html (layout minimo, para login y registro). " +
        "Cada template hijo hereda del base correcto segun su contexto."
      ),

      subtitulo("4.3  Bootstrap y Bootstrap Icons — instalacion local"),
      parrafo(
        "La CDN de Bootstrap (cdn.jsdelivr.net) estaba bloqueada en mi entorno de " +
        "desarrollo. La solucion fue descargar los archivos localmente y servirlos " +
        "desde la carpeta static/ del proyecto."
      ),
      parrafo("Archivos descargados y ubicados en static/:"),
      viñeta("css/bootstrap.min.css — Bootstrap 5.3.3"),
      viñeta("css/bootstrap-icons.min.css — Bootstrap Icons 1.11.3"),
      viñeta("fonts/bootstrap-icons.woff2, fonts/bootstrap-icons.woff — fuentes de iconos"),
      viñeta("js/bootstrap.bundle.min.js — JavaScript de Bootstrap con Popper incluido"),
      viñeta("css/main.css — estilos personalizados del sistema"),

      subtitulo("4.4  Correccion del error en historial de predicciones"),
      parrafo(
        "En el template templates/prediccion/historial.html habia una linea invalida " +
        "que causaba TemplateSyntaxError:"
      ),
      codigo("{% for nombre, riesgo, nivel in p.nivel_diabetes,p.riesgo_diabetes %}{% endfor %}"),
      parrafo(
        "Esta linea era un vestigio de un refactor incompleto. Las barras de riesgo ya " +
        "estaban correctamente renderizadas por los bloques div debajo. Simplemente " +
        "elimine esa linea y el error desaparecio."
      ),

      // ═══════════════════════════════════════════════════════ FASE 5
      separador(),
      titulo("Fase 5 — Motor de prediccion de riesgo"),

      subtitulo("5.1  Arquitectura del servicio de prediccion"),
      parrafo(
        "El motor de prediccion esta en prediccion/service.py. Recibe los datos clinicos " +
        "del paciente y devuelve un diccionario con el porcentaje de riesgo y el nivel " +
        "(Bajo/Medio/Alto) para cada una de las cinco enfermedades."
      ),
      parrafo(
        "La implementacion actual usa reglas clinicas basadas en umbrales medicos reconocidos " +
        "(JNC 8 para hipertension, ADA para diabetes, KDIGO para renal, etc.). Esta disenado " +
        "para ser reemplazado por modelos de Machine Learning entrenados con los datasets " +
        "que construi en la Fase 6."
      ),

      subtitulo("5.2  Logica de riesgo por enfermedad"),
      parrafo("Diabetes — factores principales:"),
      viñeta("Glucosa >= 200 mg/dL: riesgo alto"),
      viñeta("Glucosa 126-199 + IMC > 30: riesgo medio-alto"),
      viñeta("Glucosa 100-125: prediabetes, riesgo medio"),
      parrafo("Hipertension — factores principales:"),
      viñeta("Presion sistolica >= 140 o diastolica >= 90: hipertension estadio 2"),
      viñeta("Sistolica 130-139 o diastolica 80-89: hipertension estadio 1"),
      viñeta("Sistolica 120-129: elevada"),
      parrafo("Renal — factores principales:"),
      viñeta("Glucosa alta + edad > 60 + presion alta: riesgo combinado elevado"),
      parrafo("Higado graso (NAFLD) — factores principales:"),
      viñeta("IMC > 30 + colesterol > 220: riesgo alto"),
      parrafo("Insuficiencia cardiaca — factores principales:"),
      viñeta("Edad > 60 + presion sistolica > 145: combinacion de riesgo elevado"),

      subtitulo("5.3  Nivel general"),
      parrafo(
        "El nivel_general de una prediccion es el nivel mas alto de las cinco enfermedades. " +
        "Si alguna es 'Alto', el nivel general es 'Alto'. Si ninguna es 'Alto' pero alguna " +
        "es 'Medio', el general es 'Medio'. Solo si todas son 'Bajo', el general es 'Bajo'."
      ),

      // ═══════════════════════════════════════════════════════ FASE 6
      separador(),
      titulo("Fase 6 — Datasets de Machine Learning"),

      subtitulo("6.1  Dataset fuente: diabetic_data.csv"),
      parrafo(
        "Use el dataset publico 'Diabetes 130-US hospitals for years 1999-2008' disponible " +
        "en el UCI Machine Learning Repository. Contiene 101,766 registros de hospitalizaciones " +
        "de pacientes diabeticos con diagnosticos ICD-9, resultados de laboratorio y " +
        "tratamientos farmacologicos."
      ),
      parrafo(
        "El problema principal es que este dataset NO tenia directamente columnas de IMC, " +
        "glucosa en ayunas, presion arterial ni colesterol. Tuve que imputar esos valores " +
        "a partir de la informacion disponible."
      ),

      subtitulo("6.2  Estrategia de imputacion de columnas"),
      parrafo("Para cada registro real importe estas transformaciones:"),
      viñeta("edad: convertida de rango '[40-50)' a entero con distribucion normal centrada en 45"),
      viñeta("genero: 'Male' -> 1, 'Female' -> 0"),
      viñeta("glucosa: imputada desde max_glu_serum (>300->~330, >200->~230, Norm->~92) y A1Cresult (>8->~210, >7->~155)"),
      viñeta("imc: estimado desde diabetesMed, A1Cresult, max_glu_serum y edad"),
      viñeta("presion arterial: estimada con base en codigos ICD-9 de hipertension (401-405) y cardiaco (428)"),
      viñeta("colesterol: estimado desde edad, imc, medicacion y comorbilidad cardiaca"),

      subtitulo("6.3  Columna has_disease — definicion"),
      parrafo(
        "Agregar 'has_disease' fue el requerimiento central: una columna binaria que indica " +
        "si el paciente tiene o no tiene la enfermedad del dataset (1 = tiene, 0 = no tiene)."
      ),
      parrafo("Para los registros SINTETICOS (1100 filas generadas):"),
      viñeta("has_disease = 1 si risk_level == 2 (riesgo alto confirmado)"),
      viñeta("has_disease = 0 si risk_level == 0 o 1"),
      parrafo("Para los registros REALES (1500 filas de diabetic_data.csv):"),
      viñeta("hipertension.csv: has_disease = 1 si ICD-9 entre 401 y 405"),
      viñeta("renal.csv: has_disease = 1 si ICD-9 entre 580 y 589"),
      viñeta("higado_graso.csv: has_disease = 1 si ICD-9 = 571, o proxy (IMC>30 + glucosa>126 + A1C elevado)"),
      viñeta("insuficiencia_cardiaca.csv: has_disease = 1 si ICD-9 = 428"),
      viñeta("diabetes.csv: has_disease = 1 si ICD-9 entre 250.00 y 250.99"),

      subtitulo("6.4  Datasets generados — resumen"),
      parrafo("Todos los datasets tienen exactamente las mismas 9 columnas:"),
      codigo("age, gender, bmi, glucose, systolic_bp, diastolic_bp, cholesterol, risk_level, has_disease"),
      parrafo("Distribucion de registros por dataset:"),
      viñeta("hipertension.csv: 2600 filas | has_disease=1: 637 | has_disease=0: 1963"),
      viñeta("renal.csv: 2600 filas | has_disease=1: 219 | has_disease=0: 2381"),
      viñeta("higado_graso.csv: 2600 filas | has_disease=1: 291 | has_disease=0: 2309"),
      viñeta("insuficiencia_cardiaca.csv: 2600 filas | has_disease=1: 460 | has_disease=0: 2140"),
      viñeta("diabetes.csv: 2600 filas | has_disease=1: 1138 | has_disease=0: 1462"),

      subtitulo("6.5  Scripts de construccion de datasets"),
      parrafo("Cree dos scripts Python para reproducir los datasets en cualquier momento:"),
      viñeta("build_datasets.py — genera hipertension, renal, higado_graso e insuficiencia_cardiaca"),
      viñeta("build_diabetes.py — genera el dataset de diabetes con perfiles sinteticos especificos"),
      parrafo("Para ejecutarlos:"),
      codigo("python build_datasets.py"),
      codigo("python build_diabetes.py"),

      // ═══════════════════════════════════════════════════════ FASE 7
      separador(),
      titulo("Fase 7 — API REST y configuracion CORS"),

      subtitulo("7.1  Django REST Framework"),
      parrafo(
        "Instale e integre Django REST Framework para exponer endpoints de API. " +
        "Esto permite que en el futuro el frontend pueda consumir datos via JSON, " +
        "o que una aplicacion movil se conecte al sistema."
      ),
      parrafo("El endpoint disponible actualmente es:"),
      codigo("GET /usuarios/api/me/  ->  perfil del usuario autenticado en JSON"),

      subtitulo("7.2  Configuracion CORS"),
      parrafo(
        "Configure django-cors-headers para permitir solicitudes desde el frontend " +
        "en desarrollo (localhost:3000). En produccion esto se ajustara al dominio real."
      ),
      codigo("CORS_ALLOWED_ORIGINS = ["),
      codigo("    'http://localhost:3000',"),
      codigo("    'http://127.0.0.1:8000',"),
      codigo("]"),

      // ═══════════════════════════════════════════════════════ FASE 8
      separador(),
      titulo("Fase 8 — Control de versiones y GitHub"),

      subtitulo("8.1  Flujo de trabajo con Git"),
      parrafo(
        "Durante todo el desarrollo mantuve el repositorio actualizado en GitHub. " +
        "Cada conjunto de cambios significativo fue commiteado con un mensaje descriptivo " +
        "siguiendo el estandar Conventional Commits (feat:, fix:, docs:, etc.)."
      ),
      parrafo("Commits principales realizados:"),
      viñeta("feat: proyecto inicial ClinicalLens — estructura base del proyecto"),
      viñeta("feat: templates base y autenticacion — login, registro, dashboard"),
      viñeta("fix: correccion template prediccion historial — eliminacion de linea invalida"),
      viñeta("feat: ML datasets sinteticos 1100 registros — generacion inicial"),
      viñeta("feat: augment ML datasets with 1500 real patient records — datos reales UCI"),
      viñeta("feat: add diabetes dataset — dataset especifico para diabetes"),

      subtitulo("8.2  Repositorio"),
      parrafo("El proyecto esta disponible publicamente en:"),
      codigo("https://github.com/BryanTriguero8446/ClinicalLens"),

      // ═══════════════════════════════════════════════════════ FASE 9
      separador(),
      titulo("Fase 9 — Errores encontrados y como los resolvi"),

      subtitulo("9.1  Procesos Python en segundo plano"),
      parrafo(
        "En un momento el servidor Django no mostraba los cambios que hacia. Reiniciaba " +
        "el servidor y parecia que todo estaba bien, pero los templates seguian sin " +
        "actualizarse. Despues de investigar descubri que habia aproximadamente 9 procesos " +
        "Python activos en paralelo sirviendo versiones viejas del codigo."
      ),
      parrafo("La solucion fue terminar todos los procesos Python y reiniciar limpio:"),
      codigo("Get-Process python | Stop-Process -Force  (PowerShell)"),

      subtitulo("9.2  TemplateSyntaxError por bloque duplicado"),
      parrafo(
        "Error: 'block tag with name content appears more than once'. " +
        "Causa: intentar tener dos {% block content %} en el mismo template " +
        "dentro de un if/else. Django no permite esto porque compila el template " +
        "completo antes de evaluar condiciones."
      ),
      parrafo("Solucion: dos bases separadas — base.html y base_auth.html."),

      subtitulo("9.3  Bootstrap Icons no cargaban"),
      parrafo(
        "Los iconos aparecian como cuadros vacios. La causa era que la CDN de jsDelivr " +
        "estaba bloqueada en mi red. Descargue los archivos CSS y las fuentes .woff2 " +
        "localmente y los movi a static/css/ y static/fonts/."
      ),

      subtitulo("9.4  UnicodeEncodeError en Windows"),
      parrafo(
        "Al ejecutar build_datasets.py en Windows, Python intentaba imprimir el caracter " +
        "Unicode flecha '→' usando la codificacion cp1252 del terminal, que no lo soporta. " +
        "La solucion fue ejecutar el script con stdout reconfigurado a UTF-8:"
      ),
      codigo("python -c \"import sys,io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8'); exec(open('build_datasets.py',encoding='utf-8').read())\""),

      subtitulo("9.5  Modulo defusedxml no encontrado"),
      parrafo(
        "Al intentar procesar el documento Word con las herramientas de analisis, " +
        "aparecio el error 'ModuleNotFoundError: No module named defusedxml'. " +
        "Se soluciono instalando el modulo:"
      ),
      codigo("pip install defusedxml"),

      // ═══════════════════════════════════════════════════════ ESTADO ACTUAL
      separador(),
      titulo("Estado actual del proyecto"),

      parrafo(
        "A la fecha de elaboracion de este guion, el proyecto ClinicalLens tiene " +
        "las siguientes funcionalidades completamente operativas:"
      ),
      viñeta("Sistema de autenticacion: registro, login y logout con correo electronico"),
      viñeta("Control de roles: paciente y administrador con dashboards diferenciados"),
      viñeta("Registro de datos clinicos por paciente"),
      viñeta("Motor de prediccion de riesgo para 5 enfermedades"),
      viñeta("Historial de predicciones con barras de riesgo visuales"),
      viñeta("Sistema de alertas para pacientes"),
      viñeta("Exportacion de predicciones a CSV"),
      viñeta("5 datasets de ML listos para entrenamiento (13,000 registros en total)"),
      viñeta("API REST con Django REST Framework"),
      viñeta("Repositorio en GitHub con historial de commits"),

      parrafo(
        "Funcionalidades planificadas para las siguientes fases:"
      ),
      viñeta("Entrenamiento de modelos ML con scikit-learn y exportacion a .pkl"),
      viñeta("Integracion de modelos .pkl en prediccion/service.py"),
      viñeta("Graficos interactivos con Chart.js en el dashboard"),
      viñeta("Generacion de reportes PDF por paciente"),
      viñeta("Tests automatizados con pytest-django"),
      viñeta("Despliegue en servidor de produccion"),

      // ═══════════════════════════════════════════════════════ CIERRE
      separador(),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 400, after: 200 },
        children: [new TextRun({ text: "Bryan Triguero — UNIFRANZ 2025", bold: true, size: 24, font: "Arial", color: AZUL })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "ClinicalLens — Sistema Web Predictivo de Salud", italics: true, size: 20, font: "Arial", color: GRIS })]
      }),
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("ClinicalLens_Guion.docx", buf);
  console.log("Generado: ClinicalLens_Guion.docx");
});
