from .base import *

DEBUG=True
ALLOWED_HOSTS=['*']

print("development settings loaded")

# CORS_ALLOWED_ORIGINS = [
#     "https://example.com",
#     "http://localhost:3000",  # Example: Allow a frontend running on localhost
#     "http://127.0.0.1:3000",  # Example: Allow a frontend running on localhost
#     "http://172.20.0.1:3000",
# ]
# CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:3000","http://localhost:3000","http://172.20.0.1:3000"]

AUTH_COOKIE_NAME = 'refresh_token'
AUTH_COOKIE_SECURE = False
AUTH_COOKIE_HTTP_ONLY = True
AUTH_COOKIE_SAMESITE = 'Lax'
AUTH_COOKIE_PATH = '/'


ROLE_COOKIE_NAME = 'role'
ROLE_COOKIE_SECURE = False
ROLE_COOKIE_HTTP_ONLY = True
ROLE_COOKIE_SAMESITE = 'Lax'


SESSION_COOKIE_SECURE = False
# CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "Lax"

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = ['rest_framework.renderers.JSONRenderer',
                                              'rest_framework.renderers.BrowsableAPIRenderer'
                                              ]