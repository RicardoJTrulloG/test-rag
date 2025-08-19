FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Requisitos
COPY docker/api/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Código
COPY backend/ /app/
# Uvicorn/Gunicorn se lanzan desde docker-compose
EXPOSE 8000
USER root
