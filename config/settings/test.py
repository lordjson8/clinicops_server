from .base import *

DEBUG = False
ALLOWED_HOSTS = ['*']

# Use a faster password hasher in tests (Argon2 is slow by design)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
