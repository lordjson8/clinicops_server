# =============================================================================
# Dockerfile for Railway Deployment
#
# HOW THIS WORKS:
# Railway builds this Dockerfile, creates a container image, and runs it.
# Unlike docker-compose, PostgreSQL and Redis are EXTERNAL managed services
# provided by Railway plugins — so we don't need to wait for them to start.
#
# This is a "multi-stage build":
#   Stage 1 (builder): Installs all dependencies and creates wheel files
#   Stage 2 (production): Only copies the built wheels — smaller final image
# =============================================================================

# --- Stage 1: Builder ---
# This stage installs all Python packages and compiles them into wheel files.
# Wheels are pre-built packages that install faster than building from source.
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system libraries needed to COMPILE Python packages
# (libpq-dev is needed to compile the PostgreSQL driver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels
COPY requirements/ ./requirements/
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels \
    -r requirements/production.txt


# --- Stage 2: Production ---
# This stage is the actual image that runs on Railway.
# It only has runtime dependencies — no compilers, no build tools.
FROM python:3.11-slim AS production

# Create a non-root user for security
# (never run production apps as root)
RUN groupadd -r clinicops && useradd -r -g clinicops clinicops

WORKDIR /app

# Install only RUNTIME system libraries (not build tools)
# libpq5 = PostgreSQL client library (to talk to the DB)
# curl = needed for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages from the wheels we built in Stage 1
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy application code
COPY --chown=clinicops:clinicops . .

# Collect static files at build time (faster deploys)
RUN SECRET_KEY=build-placeholder ENV=production \
    python manage.py collectstatic --noinput

# Switch to non-root user
USER clinicops

# Tell Python not to buffer output (so you see logs in real-time on Railway)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    ENV=production

EXPOSE 8000

# Railway uses this to check if your app is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command: run Django with Gunicorn
# Railway can override this for worker/beat services
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 4 --threads 2 config.wsgi:application"]
