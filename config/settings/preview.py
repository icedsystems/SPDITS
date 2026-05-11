"""
Local/preview settings for running ICED SPDITS in a lightweight
development environment using SQLite (no PostgreSQL, Redis, or Docker required).
"""
import os
from .base import *

DEBUG = True
SECRET_KEY = 'django-insecure-preview-key-only-not-for-production'

ALLOWED_HOSTS = ['*']

# --- SQLite ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'preview.db',
    }
}

# --- Local memory cache (no Redis) ---
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# --- Database sessions (no Redis) ---
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# --- Email to console ---
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# --- Celery: run tasks eagerly and in-process ---
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# --- Static files: simple storage (no manifest hashing) ---
STATICFILES_STORAGE = 'whitenoise.storage.StaticFilesStorage'

# --- CSRF: trust local and proxy origins ---
_extra_domains = os.environ.get('TRUSTED_DOMAINS', '')
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
for _d in _extra_domains.split(','):
    _d = _d.strip()
    if _d:
        CSRF_TRUSTED_ORIGINS.append(f'https://{_d}')

# --- Port ---
PORT = int(os.environ.get('PORT', 8000))

# --- Silence ratelimit check (needs shared cache; fine for preview) ---
SILENCED_SYSTEM_CHECKS = ['django_ratelimit.E003']

# --- Logging: simpler for preview ---
LOGGING['root']['level'] = 'WARNING'
