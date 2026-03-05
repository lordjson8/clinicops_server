from .base import *
import dj_database_url
from decouple import config

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

# --- Security ---
# Railway (and most cloud platforms) sit behind a reverse proxy that handles SSL.
# This tells Django to trust the X-Forwarded-Proto header from the proxy.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CORS_ALLOWED_ORIGINS = [
    "https://example.com",
    "http://localhost:3000",  # Example: Allow a frontend running on localhost
    "http://127.0.0.1:3000",  # Example: Allow a frontend running on localhost
]
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:3000","http://localhost:3000"]

# SESSION_COOKIE_SECURE = False
# CSRF_COOKIE_SAMESITE = "Lax"
# CSRF_COOKIE_SECURE = False
# SESSION_COOKIE_SAMESITE = "Lax"

# --- Database ---
# Railway provides a DATABASE_URL environment variable when you add a PostgreSQL plugin.
# dj-database-url parses it into the format Django expects.
# If DATABASE_URL is not set, it falls back to the base.py settings (individual vars).
db_from_env = dj_database_url.config(conn_max_age=600)
if db_from_env:
    DATABASES = {'default': db_from_env}

# --- Static Files ---
STATIC_ROOT = BASE_DIR / 'staticfiles'

MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}


REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = ['rest_framework.renderers.JSONRenderer',
                                            #   'rest_framework.renderers.BrowsableAPIRenderer'
                                              ]
AUTH_COOKIE_NAME = 'refresh_token'
AUTH_COOKIE_SECURE = True
AUTH_COOKIE_HTTP_ONLY = True
AUTH_COOKIE_SAMESITE = 'None'
AUTH_COOKIE_PATH = '/api/v1/auth/'

ROLE_COOKIE_NAME = 'role'
ROLE_COOKIE_SECURE = True
ROLE_COOKIE_HTTP_ONLY = True
ROLE_COOKIE_SAMESITE = 'None'