#!/bin/bash

# Script pour démarrer Celery Beat (scheduler)

cd "$(dirname "$0")/.."

# Activer l'environnement virtuel si présent
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Démarrer Celery Beat
celery -A app.core.celery_app:celery_app beat \
    --loglevel=info \
    --pidfile=celerybeat.pid
