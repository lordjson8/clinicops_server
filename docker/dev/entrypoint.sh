#!/bin/bash

# This is the entrypoint script for the development environment.
# It simply starts the Django development server.
# Migrations are handled by a separate 'migrate' service in docker-compose.yml.

set -e

echo "Starting Django development server..."
python manage.py runserver 0.0.0.0:8000
