from pathlib import Path
from decouple import config
import os

# 🔥 BASE_DIR (FALTABA)
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.26.6']

# 🔥 APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Librerías
    'rest_framework',
    'corsheaders',

    # Apps
    'usuarios',
    'pacientes',
    'clinico',
    'prediccion',
    'reportes',
    'alertas',
]

# 🔥 MIDDLEWARE
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 🔥 URLs y WSGI (FALTABAN)
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

# 🔥 DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

# 🔥 TEMPLATES (CORREGIDO)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # ✅ AGREGADO
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',  # ✅ AGREGADO
            ],
        },
    },
]


# 🔥 STATIC
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]  # ✅ AGREGADO
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')    # ✅ AGREGADO

# 🔥 CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:8000",
]

# 🔥 REST
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES':      ('Bearer',),
}

INSTALLED_APPS_JWT = ['rest_framework_simplejwt']

# 🔥 IDIOMA Y ZONA
LANGUAGE_CODE = 'es-bo'
TIME_ZONE = 'America/La_Paz'

USE_I18N = True
USE_TZ = True

AUTH_USER_MODEL = 'usuarios.Usuario'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')           # ✅ AGREGADO

# ── Email ──────────────────────────────────────────────────────────────────
# En desarrollo usa 'console'; en producción configura SMTP en .env
EMAIL_BACKEND  = config('EMAIL_BACKEND',  default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST     = config('EMAIL_HOST',     default='smtp.gmail.com')
EMAIL_PORT     = config('EMAIL_PORT',     default=587, cast=int)
EMAIL_USE_TLS  = config('EMAIL_USE_TLS',  default=True, cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL',  default='ClinicalLens <noreply@clinicallens.com>')
