# Global config
PROJECT_NAME := clinicops-server
ENV ?= dev

COMPOSE := docker compose
COMPOSE_FILE := compose.$(ENV).yml
ENV_FILE := .env.$(ENV)

# Service Names (must match compose files)
DJANGO := backend
CELERY := celery
CELERY_BEAT := celery-beat
DB := db

.DEFAULT_GOAL := help

# Safety checks
guard-prod:
ifeq ($(ENV),prod)
	@echo "WARNING: Running a potentially destructive command in production environment"
	@read -p "Are you sure? [y/N] " ans && [ $${ans:-N} = y ]
endif

# Core Docker Commands
build:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) build

up:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) up

up-d:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) up -d

down:
	$(COMPOSE) -f $(COMPOSE_FILE) down

down-v: guard-prod
	$(COMPOSE) -f $(COMPOSE_FILE) down -v

restart:
	$(MAKE) down
	$(MAKE) up

logs:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f

ps:
	$(COMPOSE) -f $(COMPOSE_FILE) ps

# Django Commands
shell:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) exec $(DJANGO) python manage.py shell

migrate:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) exec $(DJANGO) python manage.py migrate

makemigrations:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) exec $(DJANGO) python manage.py makemigrations

superuser:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) exec $(DJANGO) python manage.py createsuperuser

collectstatic:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) exec $(DJANGO) python manage.py collectstatic --noinput

test:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) exec $(DJANGO) python manage.py test

# Celery Commands
celery-logs:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f $(CELERY)

beat-logs:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f $(CELERY_BEAT)

# Database Commands
db-shell:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) exec $(DB) psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

# Maintenance
clean: guard-prod
	$(COMPOSE) -f $(COMPOSE_FILE) down -v --remove-orphans
	docker system prune -f

reset: guard-prod
	$(MAKE) down-v
	$(MAKE) build
	$(MAKE) up

# ==============================
# Help
# ==============================
help:
	@echo ""
	@echo "Usage:"
	@echo "  make <command> ENV=dev|prod"
	@echo ""
	@echo "Examples:"
	@echo "  make up ENV=dev"
	@echo "  make migrate ENV=prod"
	@echo "  make build ENV=prod"
	@echo ""
	@echo "Commands:"
	@echo "  build, up, up-d, down, restart, logs, ps"
	@echo "  migrate, makemigrations, superuser, test, collectstatic"
	@echo "  celery-logs, beat-logs"
	@echo "  db-shell"
	@echo "  clean, reset"
	@echo ""
