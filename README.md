# 🏥 ClinicalLens

**Sistema Predictivo de Riesgo de Enfermedades Crónicas con Inteligencia Artificial**

Un análisis de riesgo de diabetes, hipertensión, enfermedad renal crónica, hígado graso e insuficiencia cardíaca basado en parámetros clínicos y antecedentes familiares, con soporte para múltiples modelos ML calibrados.

---

## 📋 Descripción del Proyecto

ClinicalLens es una aplicación web desarrollada en **Django** + **DRF** con **Inteligencia Artificial** que:

- 📊 Registra parámetros clínicos de pacientes (glucosa, presión arterial, IMC, colesterol, etc.)
- 🤖 Predice el riesgo de 5 enfermedades crónicas mediante modelos entrenados (Random Forest, XGBoost, Árbol de Decisión)
- 👨‍👩‍👦 Incorpora antecedentes familiares con multiplicadores estadísticos (ADA, ESC, JNC 8)
- 🔐 Control de acceso basado en roles (RBAC): Paciente / Administrador
- 🔔 Sistema de alertas en tiempo real con predicción de progresión temporal
- 📱 Interfaz responsiva (web + mobile)
- 🛡️ Autenticación JWT + sesiones Django
- 📈 Dashboard administrativo con métricas y monitoreo de registros

---

## 🚀 Stack Tecnológico

### Backend
- **Python 3.10+** | **Django 5.x**
- **Django REST Framework (DRF)** | **djangorestframework-simplejwt**
- **MySQL 8.x** (base de datos)
- **Scikit-learn** | **Pandas** | **NumPy** | **XGBoost** (Machine Learning)

### Frontend
- **HTML5** | **CSS3** | **Bootstrap 5**
- **JavaScript (ES6+)** | **Fetch API**
- **Bootstrap Icons**

### DevOps & Testing
- **Git** | **GitHub**
- **Django Testing Framework**
- **Pytest** (para tests adicionales)

---

## 📦 Instalación

### Requisitos previos
- Python 3.10+ 
- MySQL 8.x
- Virtual environment

### Pasos

```bash
# 1. Clonar repositorio
git clone https://github.com/[TU_USUARIO]/clinical_lens.git
cd clinical_lens

# 2. Crear y activar venv
python -m venv venv
venv\Scripts\activate  # Windows
# o: source venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de BD, JWT, email, etc.

# 5. Aplicar migraciones
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser

# 7. Ejecutar servidor
python manage.py runserver 0.0.0.0:8000
```

**Acceso**:
- 🌐 App: http://localhost:8000/
- 🔧 Admin: http://localhost:8000/admin/

---

## 👥 Equipo

| Nombre | Rol | Área |
|--------|-----|------|
| **Bryan B. Triguero Choquehuanca** | Líder de Proyecto | Modelo Predictivo & ML |
| **Belén C. Velasco Taquichiri** | Desarrolladora Backend | Lógica de Negocio, CRUD & BD |
| **Melanie I. Villca Copa** | Desarrolladora Backend | Datos Clínicos & API REST |
| **Edrian Pinto Rojas** | Desarrollador Frontend | Vistas, Formularios & Validaciones |
| **Adrian R. Martínez Quiroga** | Desarrollador Frontend | Dashboard, Gráficos & Integración API |
| **Roberto D. Chui Ticona** | Especialista en Seguridad | JWT, RBAC, Encriptación & Auditoría |

---

## 🎓 Contexto Académico

**Institución**: Universidad Privada Franz Tamayo  
**Facultad**: Ingeniería  
**Asignatura**: Testing & Quality Assurance  
**Semestre**: 7°  
**Docente**: Ing. Ivan Bernardo Céspedes Montano  
**Período**: Marzo — Mayo 2026

---

## 📚 Documentación

- **[CONTRIBUTING.md](./CONTRIBUTING.md)** — Guía para contribuir
- **[API.md](./API.md)** — Documentación de endpoints REST
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — Arquitectura del sistema
- **[TESTING.md](./TESTING.md)** — Plan de pruebas

---

## 🔐 Seguridad

- ✅ Autenticación con **JWT** (Bearer token)
- ✅ Cifrado de contraseñas con **bcrypt**
- ✅ Control de acceso basado en roles (**RBAC**)
- ✅ Validación de entrada en formularios + backend
- ✅ Logs de auditoría para acciones administrativas
- ✅ HTTPS recomendado en producción
- ⚠️ Los datos de salud son sensibles; cumple HIPAA/confidencialidad local

---

## 📊 Funcionalidades Principales

### 1️⃣ Gestión de Usuarios
- Registro y verificación por correo (OTP de 6 caracteres)
- Autenticación con JWT + sesión
- Recuperación de contraseña

### 2️⃣ Registro Clínico
- Formulario biométrico con validaciones en tiempo real
- Cálculo automático de IMC
- Historial de registros por paciente

### 3️⃣ Predicción de Riesgo
- Análisis multimodelo (ML + reglas clínicas)
- Ajuste por antecedentes familiares (opcional)
- Estimación de progresión temporal
- Soporte para 5 enfermedades simultáneamente

### 4️⃣ Alertas & Reportes
- Alertas automáticas por valores fuera de rango
- Notificaciones por correo
- Exportación a CSV/PDF
- Historial de alertas

### 5️⃣ Dashboard Administrativo
- Estadísticas globales (pacientes, registros, predicciones)
- Monitoreo en tiempo real de nuevos registros
- Gestión de usuarios

---

## 🧪 Testing

```bash
# Ejecutar todos los tests
python manage.py test

# Tests específicos por app
python manage.py test usuarios
python manage.py test clinico
python manage.py test prediccion

# Con coverage
coverage run --source='.' manage.py test
coverage report
```

**Cobertura esperada**: >80%

---

## 📝 Licencia

Este proyecto es de carácter educativo desarrollado para la Universidad Privada Franz Tamayo.  
Uso académico permitido con crédito del equipo original.

---

## 📧 Contacto & Soporte

Para consultas o issues, contacta a:
- **Bryan Triguero**: [brayantch008@gmail.com](mailto:brayantch008@gmail.com)
- **Issues**: [GitHub Issues](https://github.com/[TU_USUARIO]/clinical_lens/issues)

---

**Última actualización**: 27 de Mayo de 2026  
**Versión**: 1.0.0 (Release Candidate)

---

<div align="center">

### Desarrollado con ❤️ por el equipo UNIFRANZ 2026

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Django](https://img.shields.io/badge/Django-5.x-green)
![MySQL](https://img.shields.io/badge/MySQL-8.x-orange)
![Status](https://img.shields.io/badge/Status-Active-success)

</div>
