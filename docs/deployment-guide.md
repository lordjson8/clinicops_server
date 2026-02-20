# Django Deployment & CI/CD: From Zero to Production

> A comprehensive guide using the ClinicOps project as a real-world example.
> Written for developers who are new to deployment and want to truly understand
> every layer — not just copy-paste commands.

---

## Table of Contents

- [Part 1: Foundations — How the Web Actually Works](#part-1-foundations--how-the-web-actually-works)
- [Part 2: What "Deployment" Actually Means](#part-2-what-deployment-actually-means)
- [Part 3: Docker — Packaging Your App](#part-3-docker--packaging-your-app)
- [Part 4: Docker Compose — Running Multiple Containers](#part-4-docker-compose--running-multiple-containers)
- [Part 5: Environment Variables & Secrets](#part-5-environment-variables--secrets)
- [Part 6: Django Production Settings](#part-6-django-production-settings)
- [Part 7: CI/CD — What It Is and Why You Need It](#part-7-cicd--what-it-is-and-why-you-need-it)
- [Part 8: GitHub Actions — Deep Dive](#part-8-github-actions--deep-dive)
- [Part 9: Railway — Cloud Deployment](#part-9-railway--cloud-deployment)
- [Part 10: Putting It All Together — The Full Pipeline](#part-10-putting-it-all-together--the-full-pipeline)
- [Part 11: Intermediate Concepts](#part-11-intermediate-concepts)
- [Part 12: Senior-Level Concepts](#part-12-senior-level-concepts)
- [Part 13: Troubleshooting Guide](#part-13-troubleshooting-guide)
- [Glossary](#glossary)

---

## Part 1: Foundations — How the Web Actually Works

Before you deploy anything, you need to understand what happens when someone
visits your API.

### The Request-Response Cycle

```
User's Browser/App
       │
       │  HTTP Request: GET /api/v1/patients/
       ▼
┌─────────────────┐
│   The Internet   │   (DNS lookup, TCP connection, TLS handshake)
└────────┬────────┘
         ▼
┌─────────────────┐
│  Reverse Proxy   │   (Railway's router / Nginx / Cloudflare)
│  Handles SSL     │   Terminates HTTPS, forwards plain HTTP to your app
└────────┬────────┘
         ▼
┌─────────────────┐
│    Gunicorn      │   (WSGI server — speaks HTTP and Python)
│    4 workers     │   Each worker handles one request at a time
└────────┬────────┘
         ▼
┌─────────────────┐
│     Django       │   (Your code — URL routing, views, serializers)
│                  │   Talks to PostgreSQL, Redis, etc.
└────────┬────────┘
         ▼
┌─────────────────┐
│   PostgreSQL     │   (Your data lives here)
└─────────────────┘
```

### Why Can't Django Serve Itself in Production?

When you run `python manage.py runserver`, Django starts a **development server**.
This server:
- Handles only **one request at a time**
- Has **no security hardening**
- Serves static files **inefficiently**
- Will **crash** under real traffic

In production, you use **Gunicorn** (or uWSGI) which:
- Spawns multiple **worker processes** (your project uses 4)
- Each worker handles requests independently
- Can handle hundreds of concurrent users
- Is battle-tested for production traffic

This is configured in your `Dockerfile`:
```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "config.wsgi:application"]
```

Breaking this down:
- `--bind 0.0.0.0:8000` — Listen on all network interfaces, port 8000
- `--workers 4` — Spawn 4 separate Python processes
- `--threads 2` — Each worker has 2 threads (so 8 concurrent requests max)
- `config.wsgi:application` — The Python path to your WSGI app (defined in `config/wsgi.py`)

---

## Part 2: What "Deployment" Actually Means

"Deployment" = getting your code from your laptop to a server where users can access it.

### Development vs Production

| Aspect | Development (your laptop) | Production (Railway) |
|--------|---------------------------|----------------------|
| Server | `manage.py runserver` | Gunicorn with 4 workers |
| Database | SQLite or local PostgreSQL | Managed PostgreSQL (Railway plugin) |
| Static files | Django serves them | WhiteNoise serves them |
| Debug mode | `DEBUG=True` (shows error details) | `DEBUG=False` (shows generic errors) |
| HTTPS | Not used | Required (Railway handles it) |
| Secrets | In `.env` file on disk | In Railway's dashboard (encrypted) |
| URL | `http://localhost:8000` | `https://your-app.up.railway.app` |

### The Deployment Spectrum

There are many ways to deploy, from simple to complex:

```
Simplest                                                    Most Complex
   │                                                            │
   ▼                                                            ▼
 Railway    →    Render    →    VPS + Docker    →    Kubernetes
 Heroku          Fly.io         (DigitalOcean)       (AWS EKS)
                                (Hetzner)
```

**Railway/Heroku/Render** (Platform-as-a-Service / PaaS):
- You push code, they handle everything else
- Good for: startups, MVPs, small-medium apps
- Cost: $5-50/month

**VPS + Docker** (you rent a server):
- You manage the server, install Docker, run your containers
- Good for: when you need more control or cost savings
- Cost: $5-20/month but more work

**Kubernetes** (container orchestration):
- Automatically scales, heals, and manages hundreds of containers
- Good for: large-scale apps with millions of users
- Cost: complex, usually $100+/month

For ClinicOps, **Railway is the right choice** — it gives you managed PostgreSQL,
Redis, and automatic deployments without managing servers.

---

## Part 3: Docker — Packaging Your App

### What Problem Does Docker Solve?

The classic problem: "It works on my machine!"

Without Docker:
- Developer A has Python 3.11, Developer B has Python 3.12
- The server has different system libraries than your laptop
- Installing PostgreSQL drivers differs between macOS, Ubuntu, and Alpine Linux

With Docker:
- You define **exactly** what OS, Python version, and libraries to use
- Everyone (developers, CI, production) runs the **identical** environment

### Anatomy of a Dockerfile

Let's walk through your production Dockerfile (`Dockerfile` at root) line by line:

```dockerfile
# ---- STAGE 1: Builder ----
# WHY two stages? Because build tools (gcc, make) are ~400MB.
# We only need them to COMPILE packages, not to RUN the app.
# Multi-stage builds keep the final image small (~200MB vs ~600MB).

FROM python:3.11-slim AS builder
# Start from an official Python image.
# "slim" = Debian without extras. "alpine" = even smaller but can cause issues.
# "AS builder" = name this stage so we can reference it later.

WORKDIR /app
# All subsequent commands run inside /app in the container.
# Think of it like "cd /app".

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \    # gcc, make — needed to compile C extensions
    libpq-dev \          # PostgreSQL client headers — needed to compile psycopg
    && rm -rf /var/lib/apt/lists/*
# Install system packages needed to COMPILE Python packages.
# "rm -rf /var/lib/apt/lists/*" cleans up apt cache to save space.

COPY requirements/ ./requirements/
# Copy ONLY the requirements folder first.
# WHY? Docker caches each layer. If requirements haven't changed,
# Docker skips the pip install step entirely. This is called "layer caching"
# and it makes rebuilds much faster.

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels \
    -r requirements/production.txt
# "pip wheel" builds .whl files (pre-compiled packages).
# These are like .exe files — they install instantly without compiling.


# ---- STAGE 2: Production ----
FROM python:3.11-slim AS production
# Start fresh from a clean Python image.
# The build tools from Stage 1 are NOT included.

RUN groupadd -r clinicops && useradd -r -g clinicops clinicops
# Create a non-root user. NEVER run production apps as root.
# If an attacker exploits your app, they only get "clinicops" permissions,
# not full system access.

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \    # PostgreSQL client library (RUNTIME, not build headers)
    curl \      # Needed for health checks
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/wheels /wheels
# Copy the pre-built wheel files from Stage 1.
# This is the magic of multi-stage builds.

RUN pip install --no-cache /wheels/*
# Install all packages from wheels. No compilation needed = fast.

COPY --chown=clinicops:clinicops . .
# Copy your entire project code. --chown sets ownership to our non-root user.

RUN SECRET_KEY=build-placeholder ENV=production \
    python manage.py collectstatic --noinput
# Collect static files (CSS, JS, images) into staticfiles/ directory.
# We use a dummy SECRET_KEY because Django needs one to start,
# but we don't need a real one just to copy files.

USER clinicops
# From this point, everything runs as the non-root user.

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    ENV=production
# PYTHONDONTWRITEBYTECODE=1: Don't create .pyc files (saves disk in container)
# PYTHONUNBUFFERED=1: Print output immediately (so logs show up in real-time)

EXPOSE 8000
# Document that this container listens on port 8000.
# This doesn't actually open the port — it's just metadata.

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1
# Every 30 seconds, Docker/Railway hits /health/ to check if the app is alive.
# If it fails 3 times, the container is considered unhealthy and gets restarted.

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn ..."]
# The command that runs when the container starts.
# 1. Run migrations (update database schema)
# 2. Start Gunicorn (serve your API)
```

### Key Docker Concepts

**Image vs Container:**
- **Image** = a blueprint (like a class in Python). Built from a Dockerfile.
- **Container** = a running instance of an image (like an object). You can run multiple
  containers from the same image.

```
Dockerfile  →  docker build  →  Image  →  docker run  →  Container
(recipe)                      (blueprint)                (running app)
```

**Layers and Caching:**
Every line in a Dockerfile creates a **layer**. Docker caches layers.
If a layer hasn't changed, Docker reuses it instead of rebuilding.

```dockerfile
COPY requirements/ ./requirements/     # Layer 1: changes rarely
RUN pip install -r requirements.txt    # Layer 2: only rebuilds if requirements changed
COPY . .                               # Layer 3: changes on every code change
```

This is why we copy requirements BEFORE copying code — so pip install
is cached unless dependencies actually change.

**Common Docker Commands:**

```bash
# Build an image from a Dockerfile
docker build -t clinicops:latest .

# Run a container from an image
docker run -p 8000:8000 clinicops:latest

# List running containers
docker ps

# View container logs
docker logs <container-id>

# Open a shell inside a running container
docker exec -it <container-id> bash

# Stop a container
docker stop <container-id>

# Remove all stopped containers and unused images
docker system prune
```

---

## Part 4: Docker Compose — Running Multiple Containers

### The Problem

Your app needs multiple services:
- Django (web server)
- PostgreSQL (database)
- Redis (cache + message broker)
- Celery Worker (background jobs)
- Celery Beat (scheduled tasks)

You COULD start each one manually:
```bash
docker run postgres:15-alpine ...
docker run redis:7-alpine ...
docker run clinicops-backend ...
docker run clinicops-celery ...
```

But that's tedious and error-prone. Docker Compose lets you define all services
in one file and start everything with one command.

### Anatomy of docker-compose (compose.prod.yml)

```yaml
services:
  # --- SERVICE 1: PostgreSQL Database ---
  db:
    image: postgres:15-alpine          # Use the official PostgreSQL image
    container_name: clinicops_prod_db
    env_file: .env.prod                # Load DB credentials from this file
    volumes:
      - prod_postgres_data:/var/lib/postgresql/data   # Persist data on disk
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s                    # Check every 10 seconds
      timeout: 5s                      # Fail if check takes > 5 seconds
      retries: 5                       # Unhealthy after 5 failures
    restart: always                    # Restart if the container crashes

  # --- SERVICE 2: Redis ---
  redis:
    image: redis:7-alpine
    container_name: clinicops_prod_redis
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always

  # --- SERVICE 3: Django Backend ---
  backend:
    build:
      context: .                       # Build from current directory
      dockerfile: docker/prod/Dockerfile
    container_name: clinicops_prod_backend
    env_file: .env.prod
    environment:                       # Additional env vars (override .env.prod)
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - DATABASE_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      # Note: "db" above refers to the service name, not a hostname.
      # Docker Compose creates a network where services can reach each other by name.
    ports:
      - "8000:8000"                    # Map host port 8000 → container port 8000
    depends_on:
      db:
        condition: service_healthy     # Don't start until PostgreSQL is healthy
      redis:
        condition: service_healthy     # Don't start until Redis is healthy
    restart: always

  # --- SERVICE 4: Celery Worker ---
  celery:
    build:
      context: .
      dockerfile: docker/prod/Dockerfile
    command: celery -A config worker -l info    # Override the default CMD
    # This runs Celery instead of Gunicorn, using the SAME Docker image.
    env_file: .env.prod
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: always

  # --- SERVICE 5: Celery Beat ---
  celery-beat:
    build:
      context: .
      dockerfile: docker/prod/Dockerfile
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file: .env.prod
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: always

# Named volumes persist data between container restarts
volumes:
  prod_postgres_data:
```

### Docker Compose vs Railway

| Feature | Docker Compose | Railway |
|---------|---------------|---------|
| Where it runs | One server you control | Railway's cloud |
| PostgreSQL | You manage it | Railway manages it |
| Redis | You manage it | Railway manages it |
| Networking | Auto (services talk by name) | Auto (services linked via env vars) |
| Scaling | Manual (edit replicas) | Click a button |
| Backups | You set them up | Railway handles it |
| SSL/HTTPS | You configure Nginx | Railway handles it |

**Key insight:** Docker Compose is for running multiple containers on ONE machine.
Railway runs each service on SEPARATE machines in the cloud. That's why
`compose.prod.yml` doesn't work on Railway — they're different paradigms.

### Common Docker Compose Commands

```bash
# Start all services (detached mode — runs in background)
docker compose -f compose.prod.yml up -d

# View logs from all services
docker compose -f compose.prod.yml logs -f

# View logs from one service
docker compose -f compose.prod.yml logs -f backend

# Stop all services
docker compose -f compose.prod.yml down

# Stop and DELETE all data (including database volumes)
docker compose -f compose.prod.yml down -v    # DANGEROUS — deletes your DB

# Rebuild images after code changes
docker compose -f compose.prod.yml up -d --build

# Run a one-off command (like Django shell)
docker compose -f compose.prod.yml exec backend python manage.py shell

# Run migrations manually
docker compose -f compose.prod.yml exec backend python manage.py migrate
```

---

## Part 5: Environment Variables & Secrets

### Why Environment Variables?

Your app needs secrets (database passwords, API keys, secret keys).
You should **NEVER** hardcode them in your code:

```python
# BAD — anyone who sees your code sees your password
DATABASES = {
    'default': {
        'PASSWORD': 'my-super-secret-password',
    }
}

# GOOD — read from environment variable
from decouple import config
DATABASES = {
    'default': {
        'PASSWORD': config('POSTGRES_PASSWORD'),
    }
}
```

### How Environment Variables Work

Environment variables are key-value pairs that exist in a process's environment.

```bash
# Set an environment variable in your terminal
export SECRET_KEY="my-secret"

# Python can read it
import os
os.environ['SECRET_KEY']  # → "my-secret"

# python-decouple reads from .env files AND environment
from decouple import config
config('SECRET_KEY')  # → "my-secret"
```

### The Environment Variable Chain

```
.env file (local development)
    │
    │  loaded by python-decouple
    ▼
config('SECRET_KEY')  →  reads from environment  →  your Django settings

Railway dashboard (production)
    │
    │  injected into container's environment by Railway
    ▼
config('SECRET_KEY')  →  reads from environment  →  your Django settings
```

The same code (`config('SECRET_KEY')`) works in both places because
python-decouple checks the environment first, then falls back to `.env` files.

### Your Environment Files Explained

```
.env.dev          → Used by compose.dev.yml (local Docker development)
.env.prod         → Used by compose.prod.yml (self-hosted production)
.env              → Used when running locally without Docker
.env.dev.example  → Template for other developers (committed to git)
.env.prod.example → Template for production setup (committed to git)
```

**Golden Rules:**
1. `.env` files with REAL secrets → in `.gitignore` (never committed)
2. `.env.example` files with FAKE values → committed to git (documentation)
3. On Railway → set variables in the dashboard (no .env files at all)

### How Your Settings Switch Between Environments

```python
# config/settings/__init__.py
env = config('ENV', default='development')

if env == 'production':
    from .production import *    # Railway sets ENV=production
elif env == 'development':
    from .development import *   # Default on your laptop
elif env == 'test':
    from .test import *          # GitHub Actions sets ENV=test
```

This pattern is called **environment-based settings**. The `ENV` variable
controls which settings file is loaded.

---

## Part 6: Django Production Settings

### What Changes Between Development and Production?

Your `config/settings/production.py` adds/changes several things:

#### 1. DEBUG = False

```python
DEBUG = config('DEBUG', default=False, cast=bool)
```

In development, `DEBUG=True` shows detailed error pages with stack traces,
SQL queries, and local variables. In production, this would expose your
code's internals to attackers. `DEBUG=False` shows a generic "Server Error" page.

#### 2. ALLOWED_HOSTS

```python
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')
```

This tells Django which domain names are valid for your app.
Without this, attackers could send requests with a fake `Host` header
and trick Django into generating URLs pointing to their malicious site.

Example: `ALLOWED_HOSTS=clinicops.up.railway.app,api.clinicops.com`

#### 3. SSL/HTTPS Configuration

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

**Why `SECURE_SSL_REDIRECT = False`?**

```
User → HTTPS → Railway Proxy → HTTP → Your Django App
                    ↑
            SSL terminates here
```

Railway's proxy handles HTTPS. It forwards requests to your app as plain HTTP,
but adds the header `X-Forwarded-Proto: https`. The `SECURE_PROXY_SSL_HEADER`
setting tells Django to trust this header.

If you set `SECURE_SSL_REDIRECT = True`, Django would see the incoming HTTP
request and try to redirect to HTTPS, but Railway's proxy would forward that
redirect as HTTP again → **infinite redirect loop**.

#### 4. DATABASE_URL

```python
import dj_database_url

db_from_env = dj_database_url.config(conn_max_age=600)
if db_from_env:
    DATABASES = {'default': db_from_env}
```

`conn_max_age=600` means "keep database connections open for 10 minutes."
Without this, Django opens a new connection for EVERY request (slow).
With it, connections are reused across requests (fast).

#### 5. WhiteNoise (Static Files)

```python
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

In development, Django serves static files (CSS, JS, images) itself.
In production, WhiteNoise serves them efficiently with:
- **Compression** (gzip/brotli — smaller files, faster downloads)
- **Cache headers** (browsers cache files, reducing server load)
- **Manifest** (adds a hash to filenames like `style.a1b2c3.css` for cache busting)

#### 6. Logging

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

In production, logs go to **stdout** (the console), which Railway captures
and shows in its dashboard. You can view them at:
Railway → Your Service → "Logs" tab.

---

## Part 7: CI/CD — What It Is and Why You Need It

### The Problem Without CI/CD

Without automation, deploying looks like this:

1. You write code on your laptop
2. You *hope* it works (maybe you run tests locally, maybe you don't)
3. You SSH into the server
4. You `git pull` the latest code
5. You run `pip install`, `migrate`, `collectstatic`
6. You restart Gunicorn
7. You pray nothing breaks

Problems:
- Step 2: Tests might not run → bugs reach production
- Step 3-6: Manual and error-prone → you might forget a step
- Step 7: If something breaks, you're scrambling to fix it live

### What CI/CD Means

**CI = Continuous Integration**
- Every time you push code, automated tests run
- If tests fail, you know immediately (before merging)
- "Continuous" = it happens on EVERY push, not just when you remember

**CD = Continuous Deployment**
- If tests pass, the code is automatically deployed to production
- No manual steps, no SSH, no praying

```
CI                              CD
┌────────────────────┐    ┌────────────────────┐
│  Push code         │    │  Tests passed?      │
│  → Run tests       │───▶│  → Deploy to        │
│  → Run linters     │    │    production        │
│  → Check security  │    │    automatically     │
└────────────────────┘    └────────────────────┘
```

### The CI/CD Pipeline

A "pipeline" is a sequence of automated steps:

```
Push to GitHub
    │
    ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Build      │────▶│    Test       │────▶│   Deploy     │
│              │     │              │     │              │
│ Install deps │     │ Run tests    │     │ railway up   │
│ Check syntax │     │ Check types  │     │              │
└─────────────┘     └──────────────┘     └──────────────┘
                          │
                     Tests fail?
                          │
                          ▼
                    ❌ Stop pipeline
                    Notify developer
```

---

## Part 8: GitHub Actions — Deep Dive

### What Is GitHub Actions?

GitHub Actions is GitHub's built-in CI/CD system. It:
- Runs on GitHub's servers (you don't need your own CI server)
- Is triggered by events (push, pull request, schedule, etc.)
- Uses YAML files to define workflows
- Is free for public repos, 2000 minutes/month for free private repos

### Key Concepts

**Workflow:** A YAML file in `.github/workflows/` that defines what to automate.
You can have multiple workflows (e.g., one for tests, one for deploys).

**Event (trigger):** What starts the workflow.
```yaml
on:
  push:                      # When code is pushed
    branches: [master]       # Only on the master branch
  pull_request:              # When a PR is opened/updated
    branches: [master]       # Only for PRs targeting master
  schedule:                  # On a schedule (cron syntax)
    - cron: '0 0 * * *'     # Daily at midnight
  workflow_dispatch:         # Manual trigger (button in GitHub UI)
```

**Job:** A set of steps that run on a fresh virtual machine.
Jobs run in parallel by default. Use `needs` to run them sequentially.

**Step:** A single command or action within a job.

**Action:** A reusable unit of code (like a function/library).
Published on the GitHub Marketplace. Examples:
- `actions/checkout@v4` — downloads your code
- `actions/setup-python@v5` — installs Python
- `actions/cache@v4` — caches dependencies between runs

**Runner:** The virtual machine that runs your job.
`runs-on: ubuntu-latest` = a fresh Ubuntu VM on GitHub's servers.

**Secret:** An encrypted variable stored in GitHub settings.
Accessed via `${{ secrets.YOUR_SECRET_NAME }}`.

### Anatomy of Your Workflow File

Let's break down `.github/workflows/deploy.yml` section by section:

```yaml
# ===== METADATA =====
name: Test & Deploy to Railway
# This name appears in the GitHub Actions tab of your repo.

# ===== TRIGGERS =====
on:
  push:
    branches: [master]
  pull_request:
    branches: [master]
# Push to master: run tests AND deploy
# PR to master: run tests only (deploy is skipped via the "if" condition)

# ===== JOBS =====
jobs:
  # --- JOB 1: TEST ---
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    # GitHub spins up a fresh Ubuntu VM for this job.
    # It has nothing installed except basic tools.
    # After the job finishes, the VM is destroyed.

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: clinicops_test_db
          POSTGRES_USER: clinicops_test_user
          POSTGRES_PASSWORD: clinicops_test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    # "services" are Docker containers that run alongside your job.
    # Think of them as temporary infrastructure.
    # GitHub starts PostgreSQL, waits for it to be healthy,
    # then runs your steps.
    # The database is EMPTY — it exists only for this test run.
    # After the job finishes, it's destroyed along with the VM.

    env:
      ENV: test
      DB_ENGINE: postgresql
      POSTGRES_HOST: localhost
      # WHY "localhost"? The PostgreSQL container's port 5432 is mapped
      # to the runner's port 5432. So from the runner's perspective,
      # PostgreSQL is at localhost:5432.
      SECRET_KEY: test-secret-key-not-for-production
      # This is a FAKE key for testing only. Never use test keys in production.

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        # This downloads your repo into the runner's filesystem.
        # Without this, the runner has NO access to your code.

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
        # Installs Python 3.11 on the runner.
        # The runner has Python pre-installed, but this ensures the exact version.

      - name: Cache pip dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements/base.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
        # Caching saves ~30-60 seconds per run.
        # "key" is based on the hash of requirements.txt.
        # If requirements haven't changed, the cache is reused.
        # If they have changed, a new cache is created.

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libpq-dev
        # Install the PostgreSQL development headers.
        # Needed to compile the psycopg PostgreSQL driver.

      - name: Install Python dependencies
        run: pip install -r requirements/base.txt
        # Install your project's Python packages.

      - name: Run migrations
        run: python manage.py migrate --noinput
        # Create the database tables in the temporary PostgreSQL.
        # --noinput means "don't ask for user input."

      - name: Run tests
        run: python manage.py test --verbosity=2
        # Run your Django test suite.
        # --verbosity=2 shows each test name and result.
        # If ANY test fails, this step fails, the job fails,
        # and the deploy job is skipped.

  # --- JOB 2: DEPLOY ---
  deploy:
    name: Deploy to Railway
    runs-on: ubuntu-latest
    needs: test
    # "needs: test" means this job WAITS for the test job to complete.
    # If the test job fails, this job is SKIPPED entirely.

    if: github.event_name == 'push' && github.ref == 'refs/heads/master'
    # Only deploy on PUSH to master.
    # Pull requests run tests but don't deploy.
    # This prevents deploying unreviewed code.

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install Railway CLI
        run: npm install -g @railway/cli
        # Install the Railway command-line tool.
        # This lets us trigger deployments from the CI runner.

      - name: Deploy to Railway
        run: railway up --detach
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        # "railway up" uploads your code to Railway and triggers a build.
        # "--detach" means don't wait for the build to finish
        # (the CI job exits, Railway builds in the background).
        # RAILWAY_TOKEN authenticates the CLI with your Railway account.
        # It's stored as a GitHub Secret (encrypted, never shown in logs).
```

### Understanding the `if` Condition

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/master'
```

This is crucial. Here's why:

| Scenario | event_name | ref | Deploy? |
|----------|-----------|-----|---------|
| Push to master | `push` | `refs/heads/master` | Yes |
| Push to feature branch | `push` | `refs/heads/feature-x` | No |
| Open PR to master | `pull_request` | `refs/pull/1/merge` | No |

Without this condition, EVERY push to ANY branch would trigger a deploy.

### GitHub Secrets

Secrets are encrypted variables that GitHub injects into your workflow.
They are:
- **Encrypted at rest** (stored securely by GitHub)
- **Masked in logs** (if a secret value appears in output, it shows `***`)
- **Not available in PRs from forks** (security against malicious PRs)

To add a secret:
1. Go to your repo on GitHub
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `RAILWAY_TOKEN`, Value: your token from Railway

### Workflow Visualization

When you push code, go to your repo → **"Actions" tab** to see:

```
Test & Deploy to Railway
├── Run Tests .............. ✅ passed (2m 15s)
│   ├── Checkout code ........... ✅ (2s)
│   ├── Set up Python 3.11 ...... ✅ (5s)
│   ├── Cache pip dependencies ... ✅ (1s, cache hit)
│   ├── Install system deps ...... ✅ (8s)
│   ├── Install Python deps ...... ✅ (45s)
│   ├── Run migrations ........... ✅ (3s)
│   └── Run tests ................ ✅ (72s)
│
└── Deploy to Railway ........ ✅ passed (45s)
    ├── Checkout code ........... ✅ (2s)
    ├── Install Railway CLI ...... ✅ (12s)
    └── Deploy to Railway ........ ✅ (31s)
```

---

## Part 9: Railway — Cloud Deployment

### What Railway Provides

Railway is a PaaS (Platform as a Service). It gives you:

1. **Docker hosting** — builds and runs your Dockerfile
2. **Managed PostgreSQL** — backups, monitoring, connection pooling
3. **Managed Redis** — no setup needed
4. **Automatic HTTPS** — free SSL certificates
5. **Custom domains** — point your domain to Railway
6. **Environment variables** — securely stored and injected
7. **Logs** — real-time log streaming
8. **Metrics** — CPU, memory, network usage
9. **Automatic restarts** — if your app crashes, Railway restarts it

### Railway Architecture

```
Your Railway Project
│
├── PostgreSQL (plugin)
│   └── Provides: DATABASE_URL
│       e.g., postgresql://postgres:abc123@monorail.proxy.rlwy.net:12345/railway
│
├── Redis (plugin)
│   └── Provides: REDIS_URL
│       e.g., redis://default:xyz789@monorail.proxy.rlwy.net:54321
│
├── Web Service (your Django app)
│   ├── Built from: Dockerfile
│   ├── Start command: (default from Dockerfile CMD)
│   ├── Variables: ENV, SECRET_KEY, ALLOWED_HOSTS, DATABASE_URL, REDIS_URL
│   ├── Domain: clinicops.up.railway.app
│   └── Health check: /health/
│
├── Celery Worker
│   ├── Built from: same Dockerfile
│   ├── Start command: celery -A config worker -l info
│   └── Variables: same as web service
│
└── Celery Beat
    ├── Built from: same Dockerfile
    ├── Start command: celery -A config beat -l info --scheduler ...
    └── Variables: same as web service
```

### How Railway Builds Your App

When you deploy (either via `railway up` or auto-deploy from GitHub):

```
Step 1: Railway clones your repo
Step 2: Railway finds your Dockerfile
Step 3: Railway runs "docker build" (just like on your laptop)
Step 4: Railway pushes the image to its internal registry
Step 5: Railway starts a container from the image
Step 6: Railway injects environment variables
Step 7: Railway runs the CMD from the Dockerfile
Step 8: Railway waits for the health check to pass
Step 9: Railway routes traffic to the new container
Step 10: Railway stops the old container (zero-downtime deploy)
```

### How Services Communicate

In docker-compose, services talk by name:
```
DATABASE_URL=postgresql://user:pass@db:5432/mydb
                                     ^^
                                     service name
```

On Railway, services talk via the internet:
```
DATABASE_URL=postgresql://user:pass@monorail.proxy.rlwy.net:12345/railway
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                     Railway's proxy URL
```

Railway's proxy handles connection routing, load balancing, and encryption.

### Variable References

Railway has a powerful feature: **variable references**. Instead of copy-pasting
the PostgreSQL URL into every service, you create a reference:

```
In your Web service variables:
  DATABASE_URL = ${{ PostgreSQL.DATABASE_URL }}

In your Celery Worker variables:
  DATABASE_URL = ${{ PostgreSQL.DATABASE_URL }}
```

If the database URL changes (e.g., Railway migrates the DB), all services
automatically get the new URL.

### Railway CLI Commands

```bash
# Login to Railway
railway login

# Link your local project to a Railway project
railway link

# Deploy your code
railway up

# Open your app in the browser
railway open

# View logs
railway logs

# Run a command in your Railway environment
railway run python manage.py createsuperuser

# View environment variables
railway variables

# Open the Railway dashboard
railway dashboard
```

---

## Part 10: Putting It All Together — The Full Pipeline

Here's the complete flow from writing code to users accessing your API:

```
Step 1: You write code on your laptop
         │
Step 2:  git add . && git commit -m "Add patient search"
         │
Step 3:  git push origin master
         │
         ▼
Step 4: GitHub receives the push
         │
         ├──▶ GitHub Actions triggers ".github/workflows/deploy.yml"
         │
Step 5:  │   JOB: test
         │   ├── Spins up Ubuntu VM
         │   ├── Starts PostgreSQL + Redis containers
         │   ├── Installs Python 3.11
         │   ├── pip install -r requirements/base.txt
         │   ├── python manage.py migrate
         │   └── python manage.py test
         │        │
         │   Tests pass? ────No───▶ ❌ Pipeline stops. You get an email.
         │        │
         │       Yes
         │        │
Step 6:  │   JOB: deploy
         │   ├── Installs Railway CLI
         │   └── railway up --detach
         │        │
         ▼        ▼
Step 7: Railway receives your code
         │
         ├── docker build (builds your image)
         ├── Starts new container
         ├── Injects DATABASE_URL, REDIS_URL, SECRET_KEY, etc.
         ├── Runs: python manage.py migrate --noinput
         ├── Runs: gunicorn --bind 0.0.0.0:$PORT ...
         ├── Waits for /health/ to return 200 OK
         ├── Routes traffic to new container
         └── Stops old container
         │
Step 8:  Users access https://clinicops.up.railway.app/api/v1/patients/
```

**Total time from `git push` to live:** ~3-5 minutes.

---

## Part 11: Intermediate Concepts

### Branch Protection Rules

Protect your `master` branch so no one (including you) can push directly:

1. GitHub → Settings → Branches → Add rule
2. Branch name pattern: `master`
3. Check: "Require status checks to pass before merging"
4. Select: "Run Tests" (your CI job)
5. Check: "Require pull request reviews before merging"

Now the workflow becomes:
```
feature branch → Pull Request → Tests run → Code review → Merge → Deploy
```

### Staging Environment

Don't deploy directly to production. Create a staging environment first:

```
main branch    → Deploy to staging    (staging.clinicops.up.railway.app)
                     │
                  Manual testing
                     │
                     ▼
release tag    → Deploy to production (clinicops.up.railway.app)
```

On Railway, create two projects:
- `clinicops-staging`
- `clinicops-production`

### Database Migrations Strategy

Migrations can be dangerous in production. Follow these rules:

1. **Never delete columns/tables directly.** First deploy code that stops using
   the column, then delete it in a later deploy.

2. **Never rename columns.** Add a new column, copy data, deploy code using the
   new column, then remove the old one.

3. **Always test migrations locally first:**
   ```bash
   python manage.py migrate --plan    # See what will run
   python manage.py migrate           # Run it
   ```

4. **Back up before migrating in production:**
   Railway → PostgreSQL service → "Backups" → Create backup

### Health Checks Explained

The health check is how Railway knows your app is alive:

```python
# config/urls.py
def health_check(request):
    return JsonResponse({"status": "ok"})
```

A more advanced health check verifies database and Redis connectivity:

```python
from django.db import connection
from django.core.cache import cache

def health_check(request):
    # Check database
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"status": "error", "db": "down"}, status=503)

    # Check Redis
    try:
        cache.set("health_check", "ok", 10)
        if cache.get("health_check") != "ok":
            raise Exception("Redis read failed")
    except Exception:
        return JsonResponse({"status": "error", "redis": "down"}, status=503)

    return JsonResponse({"status": "ok"})
```

**503** = Service Unavailable. Railway sees this and knows not to route traffic
to this container.

### Gunicorn Tuning

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", ...]
```

**How many workers?** The formula is: `(2 × CPU cores) + 1`
- Railway's free/starter plan: 1 vCPU → 3 workers
- Railway's pro plan: 2 vCPUs → 5 workers

**Workers vs Threads:**
- **Workers** = separate processes (true parallelism, more memory)
- **Threads** = lightweight within a process (share memory, good for I/O-bound work)

For a Django API (mostly I/O-bound — waiting for DB queries):
- 2-4 workers with 2-4 threads each is a good starting point.

---

## Part 12: Senior-Level Concepts

### Zero-Downtime Deployments

When Railway deploys a new version:
1. It starts the NEW container
2. It waits for the health check to pass
3. It routes traffic to the NEW container
4. It stops the OLD container

This means users never see downtime. But there's a catch:
during step 2-3, BOTH old and new containers might be running
with different code versions. Your migrations must be
**backwards-compatible** (the old code must work with the new schema).

### Container Security

Your Dockerfile already follows best practices:
- **Non-root user** (`USER clinicops`)
- **Multi-stage build** (no build tools in production)
- **Slim base image** (minimal attack surface)

Additional hardening:
- Scan your image for vulnerabilities: `docker scout cve clinicops:latest`
- Use specific image tags (not `latest`): `python:3.11.7-slim` instead of `python:3.11-slim`
- Set read-only filesystem where possible

### Monitoring and Observability

**The Three Pillars:**

1. **Logs** — What happened? (Railway provides this)
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info("Patient created", extra={"patient_id": patient.id})
   ```

2. **Metrics** — How is the system performing? (Railway dashboard)
   - CPU usage, memory usage, request count, response times

3. **Traces** — How long did each part of a request take?
   - Tools: Sentry, Datadog, OpenTelemetry
   - Shows: "This request took 2s: 50ms in Django, 1.8s in PostgreSQL, 150ms in Redis"

### Scaling Strategies

**Vertical scaling** (bigger machine):
- Railway → Service → Settings → increase memory/CPU
- Simple but has limits

**Horizontal scaling** (more machines):
- Railway → Service → Settings → increase replicas
- Works for stateless services (Django, Celery workers)
- Does NOT work for Celery Beat (only 1 instance should run)

```
                    ┌─────────────┐
                    │ Railway      │
                    │ Load Balancer│
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Django 1  │ │ Django 2  │ │ Django 3  │
        │ (replica) │ │ (replica) │ │ (replica) │
        └──────────┘ └──────────┘ └──────────┘
              │            │            │
              └────────────┼────────────┘
                           ▼
                    ┌──────────────┐
                    │  PostgreSQL   │
                    └──────────────┘
```

### Advanced CI/CD Patterns

**Matrix Testing** — test on multiple Python versions:
```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
steps:
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python-version }}
```

**Parallel Test Jobs** — split tests across multiple runners:
```yaml
strategy:
  matrix:
    test-group: ["accounts", "clinics", "patients", "billing"]
steps:
  - run: python manage.py test apps.${{ matrix.test-group }}
```

**Deployment Approvals** — require manual approval for production:
```yaml
deploy-production:
  environment:
    name: production
    url: https://clinicops.up.railway.app
  # GitHub will show a "Review deployments" button
  # Someone must click "Approve" before this job runs
```

**Rollback Strategy:**
```bash
# If a deploy breaks production, roll back to the previous deploy:
# Railway Dashboard → Service → Deployments → Click "Redeploy" on the previous one

# Or via CLI:
railway rollback
```

### Secret Rotation

Secrets should be rotated periodically (every 90 days for SECRET_KEY):

1. Generate a new SECRET_KEY:
   ```python
   from django.core.management.utils import get_random_secret_key
   print(get_random_secret_key())
   ```
2. Update it in Railway's dashboard
3. Railway automatically restarts the service with the new key

**Note:** Rotating SECRET_KEY invalidates all existing sessions and JWT tokens.
Users will need to log in again.

### Cost Optimization

Railway pricing (as of 2025):
- **Trial**: $5 free credit, no credit card needed
- **Hobby**: $5/month per user, includes $5 of usage
- **Pro**: $20/month per user, includes $10 of usage

Tips to reduce costs:
- Use `--workers 2` instead of 4 on smaller plans
- Scale Celery workers down when not processing tasks
- Use Railway's sleep feature for staging environments
- Monitor memory — Python apps can leak memory over time

---

## Part 13: Troubleshooting Guide

### Common Issues and Solutions

#### "Application failed to respond" (Railway)
**Cause:** Your app isn't listening on the right port.
**Fix:** Ensure Gunicorn binds to `0.0.0.0:${PORT:-8000}`. Railway sets the `PORT` variable.

#### Health check failing
**Cause:** `/health/` endpoint not accessible.
**Debug:**
```bash
# Test locally
curl http://localhost:8000/health/

# Check Railway logs
railway logs
```

#### "ModuleNotFoundError" in production
**Cause:** A package is in `requirements/development.txt` but not in `requirements/production.txt`.
**Fix:** Move the package to `requirements/base.txt` (shared by all environments).

#### Migrations failing on deploy
**Cause:** Migration conflict or database schema mismatch.
**Debug:**
```bash
# Run migrations manually
railway run python manage.py showmigrations
railway run python manage.py migrate --plan
```

#### Static files not loading
**Cause:** `collectstatic` didn't run, or WhiteNoise not configured.
**Fix:** Ensure the Dockerfile runs `collectstatic` and `production.py` has WhiteNoise middleware.

#### "DisallowedHost" error
**Cause:** Your Railway domain isn't in `ALLOWED_HOSTS`.
**Fix:** Add it: `ALLOWED_HOSTS=your-app.up.railway.app`

#### GitHub Actions test job failing
**Cause:** Check the specific step that failed in the Actions tab.
**Common fixes:**
- Missing system dependency → add to `apt-get install` step
- Missing env variable → add to the `env` section
- Test timeout → increase job timeout: `timeout-minutes: 15`

#### "CSRF verification failed" in production
**Cause:** Cookie secure settings or missing CSRF trusted origins.
**Fix:** Add to production.py:
```python
CSRF_TRUSTED_ORIGINS = ['https://your-app.up.railway.app']
```

---

## Glossary

| Term | Definition |
|------|-----------|
| **CI** | Continuous Integration — automatically testing code on every push |
| **CD** | Continuous Deployment — automatically deploying code after tests pass |
| **Container** | A lightweight, isolated environment that runs your app |
| **Docker** | Tool for building and running containers |
| **Docker Compose** | Tool for defining multi-container setups on one machine |
| **Dockerfile** | Recipe for building a Docker image |
| **Image** | A snapshot/blueprint of a container (built from a Dockerfile) |
| **Gunicorn** | Python WSGI HTTP server for production |
| **WSGI** | Web Server Gateway Interface — the protocol between web servers and Python apps |
| **Health check** | An endpoint the platform hits to verify your app is running |
| **Layer** | A step in a Dockerfile. Docker caches layers for faster builds |
| **Migration** | A script that changes your database schema (add/remove tables, columns) |
| **Multi-stage build** | A Dockerfile with multiple FROM statements to keep the final image small |
| **PaaS** | Platform as a Service — a cloud platform that manages infrastructure for you |
| **Pipeline** | A sequence of automated CI/CD steps |
| **Plugin** | A Railway add-on service (PostgreSQL, Redis, etc.) |
| **Reverse proxy** | A server that sits in front of your app, handling SSL and load balancing |
| **Runner** | The virtual machine that executes a GitHub Actions job |
| **Secret** | An encrypted variable (API key, password) stored securely |
| **SSL/TLS** | Encryption protocol for HTTPS |
| **Static files** | CSS, JavaScript, images — files served directly to browsers |
| **Volume** | Persistent storage that survives container restarts |
| **WhiteNoise** | Python library that serves static files efficiently in production |
| **Worker** | A Gunicorn process that handles HTTP requests |
| **Workflow** | A GitHub Actions YAML file that defines an automation pipeline |

---

## Quick Reference: Files in This Project

| File | Purpose | Used by |
|------|---------|---------|
| `Dockerfile` (root) | Railway deployment | Railway |
| `docker/prod/Dockerfile` | Self-hosted Docker deployment | docker-compose |
| `docker/dev/Dockerfile` | Local development | docker-compose |
| `compose.dev.yml` | Local development stack | You (local) |
| `compose.prod.yml` | Self-hosted production stack | You (VPS) |
| `railway.toml` | Railway build/deploy config | Railway |
| `.github/workflows/deploy.yml` | CI/CD pipeline | GitHub Actions |
| `config/settings/base.py` | Shared settings (all environments) | Django |
| `config/settings/development.py` | Development overrides | Django (local) |
| `config/settings/production.py` | Production overrides | Django (Railway) |
| `config/settings/test.py` | Test overrides | Django (CI) |
| `.env.dev` | Dev environment variables | docker-compose |
| `.env.prod` | Prod environment variables | docker-compose |
| `.env.dev.example` | Template for dev env | Documentation |
| `.env.prod.example` | Template for prod env | Documentation |
| `entrypoint.sh` | Docker-compose startup script | docker-compose |
| `requirements/base.txt` | Core Python dependencies | All environments |
| `requirements/production.txt` | Production-only dependencies | Dockerfile |
| `requirements/development.txt` | Dev-only dependencies | Local |
