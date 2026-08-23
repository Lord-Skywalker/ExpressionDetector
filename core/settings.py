"""
Django settings for ExpressionDetector.

Environment-aware: works for both local development and production (Render.com).
Local dev:    Uses SQLite, filesystem Celery broker, local media storage.
Production:   Uses Neon PostgreSQL, Upstash Redis, Cloudflare R2 object storage.

All secrets are loaded from environment variables via python-decouple.
Copy .env.example to .env and fill in your values for local overrides.
"""

from pathlib import Path
from decouple import config, Csv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


# ── Core ─────────────────────────────────────────────────────────────────────

SECRET_KEY = config("SECRET_KEY", default="django-insecure-!t@8%)cb-9l#6ti@=nsf@nf6vxov0d0^$0=mptem++=j@u$g#q")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


# ── Installed Apps ────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "analytics",
]


# ── Middleware ────────────────────────────────────────────────────────────────

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Serve static files in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# ── Database ──────────────────────────────────────────────────────────────────
# Production: set DATABASE_URL to your Neon PostgreSQL connection string.
# Local dev:  leave DATABASE_URL unset → falls back to SQLite.

_database_url = config("DATABASE_URL", default=None)

if _database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ── Static & Media Files ──────────────────────────────────────────────────────

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (uploaded videos) — stored locally on Render's disk.
# The Celery task reads the file from disk and sends it directly to HF Space,
# so no external object storage (R2/S3) is needed.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ── CORS ──────────────────────────────────────────────────────────────────────

raw_cors = config("CORS_ALLOWED_ORIGINS", default="http://localhost:3000,http://localhost:5173")
if raw_cors.strip() == "*":
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [url.strip() for url in raw_cors.split(",")]


# ── Celery ────────────────────────────────────────────────────────────────────
# Production: set REDIS_URL to your Upstash Redis URL.
# Local dev:  leave REDIS_URL unset → falls back to filesystem broker.

_redis_url = config("REDIS_URL", default=None)

if _redis_url:
    CELERY_BROKER_URL = _redis_url
    CELERY_RESULT_BACKEND = _redis_url
else:
    CELERY_BROKER_URL = "filesystem://"
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        "data_folder_in": str(BASE_DIR / "broker" / "out"),
        "data_folder_out": str(BASE_DIR / "broker" / "out"),
    }
    CELERY_RESULT_BACKEND = None

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"


# ── Google Cloud Run (ML Worker) ─────────────────────────────────────────────
# In production, the Celery task sends the video file here instead of running ML locally.
# Local dev: leave unset → Celery runs offline_processor.py directly.

ML_WORKER_URL = config("ML_WORKER_URL", default=None)
# Example: https://ml-worker-xxx-uc.a.run.app


# ── Auth password validators ──────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ── Internationalization ──────────────────────────────────────────────────────

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ── Default primary key ───────────────────────────────────────────────────────

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
