"""
Django settings for config project.

Configuration is driven by environment variables so the same code runs locally
and on Railway. Locally these come from backend/.env (loaded below); on Railway
they are set in the service's Variables tab (DATABASE_URL is injected by the
PostgreSQL plugin automatically).
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Repo root holds the frontend/ sibling of backend/. In the production image the
# built SPA lives at /app/frontend/dist; Django serves it via WhiteNoise.
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

# Load backend/.env for local development. On Railway the env vars are already
# present, so the missing file is simply ignored.
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def env_positive_float(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def env_nonnegative_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


# SECURITY WARNING: keep the secret key used in production secret!
# A throwaway default keeps local dev frictionless; production MUST set SECRET_KEY.
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-dev-only-change-me-in-production",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool("DEBUG", default=False)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

# Railway exposes the public domain of the service via this env var.
RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

CSRF_TRUSTED_ORIGINS = ["https://*.railway.app"]
if RAILWAY_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")


# Application definition

INSTALLED_APPS = [
    'corsheaders',
    'accounts',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    # WhiteNoise serves static files in production; must come right after security.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
# DATABASE_URL example: postgres://app:app@localhost:5432/app
DATABASE_URL = os.environ["DATABASE_URL"]

default_database = dj_database_url.config(
    default=DATABASE_URL,
    conn_max_age=600,
    conn_health_checks=True,
    ssl_require=not DEBUG and not DATABASE_URL.startswith("sqlite"),
)

# Keep the local SQLite database stable regardless of the directory from which
# manage.py is invoked. dj-database-url otherwise leaves relative paths tied to
# the process working directory.
if default_database["ENGINE"] == "django.db.backends.sqlite3":
    database_name = Path(default_database["NAME"])
    if not database_name.is_absolute():
        default_database["NAME"] = BASE_DIR / database_name

DATABASES = {"default": default_database}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.environ.get('TIME_ZONE', 'Europe/Berlin')

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
# The Vite build (base '/static/') is collected alongside Django's own static
# files and served by WhiteNoise. WHITENOISE_INDEX_FILE lets it resolve the SPA
# entry point.
STATICFILES_DIRS = [FRONTEND_DIST] if FRONTEND_DIST.exists() else []
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Vite already content-hashes filenames, so compress without re-hashing.
        # Manifest storage would rewrite asset names and break the references in
        # the pre-built index.html (which isn't processed through the manifest).
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
WHITENOISE_INDEX_FILE = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@example.com")


# n8n owns mission-generation LLM orchestration. Interactive chat replies keep
# using the separately configured KICOnnect connection.
N8N_MISSION_GENERATION_URL = os.environ.get("N8N_MISSION_GENERATION_URL", "").strip()
N8N_SERVICE_SECRET = os.environ.get("N8N_SERVICE_SECRET", "").strip()
N8N_CALLBACK_SECRET = os.environ.get("N8N_CALLBACK_SECRET", "").strip()
N8N_REQUEST_TIMEOUT = env_positive_float("N8N_REQUEST_TIMEOUT", 10.0)
N8N_WORKFLOW_VERSION = os.environ.get("N8N_WORKFLOW_VERSION", "v1").strip() or "v1"
MISSION_TASK_DAYS_PER_WEEK = env_nonnegative_int("MISSION_TASK_DAYS_PER_WEEK", 2)


CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS.extend([
    'http://localhost:5173',
    'http://127.0.0.1:5173',
])

SESSION_COOKIE_SAMESITE = 'Lax'

# Security hardening when running with DEBUG off (i.e. in production).
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
