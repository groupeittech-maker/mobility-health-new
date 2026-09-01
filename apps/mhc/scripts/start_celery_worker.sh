#!/bin/bash

# Script pour démarrer le worker Celery

cd "$(dirname "$0")/.."

# Activer l'environnement virtuel si présent
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Démarrer le worker Celery
celery -A app.core.celery_app:celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=default,notifications,reminders \
    --hostname=worker@%h
