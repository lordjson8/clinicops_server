FROM python:3.12.2-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser

COPY requirements /app/requirements
ARG REQUIREMENTS_FILE=requirements/development.txt

RUN pip install --no-cache-dir -r ${REQUIREMENTS_FILE}

COPY . /app/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000