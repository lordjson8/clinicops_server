import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent


env = config('ENV', default='development')


if env == 'production':
    from .production import *
elif env == 'development':
    print("env")

    from .development import *
elif env == 'test':
    from .test import *
else:
    raise ValueError(f"Invalid environment: {env}")