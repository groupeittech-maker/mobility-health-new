#!/usr/bin/env bash
# Cloud Agent — démarrage par boot : Docker + services d'infra + migrations.
# Idempotent : peut être relancé sans effet de bord.
set -euo pipefail

echo "==> Démarrage du démon Docker"
if ! sudo docker info >/dev/null 2>&1; then
  sudo service docker start 2>/dev/null || (sudo dockerd >/tmp/dockerd.log 2>&1 &)
  for _ in $(seq 1 30); do
    sudo docker info >/dev/null 2>&1 && break
    sleep 1
  done
fi

cd /workspace/apps/mhc

echo "==> Démarrage des services (Postgres, Redis, MinIO)"
sudo docker compose up -d db redis minio

echo "==> Attente de Postgres"
for _ in $(seq 1 60); do
  if sudo docker compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "==> Migrations Alembic"
export PYTHONPATH=/workspace/apps/mhc
export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/mobility_health
/workspace/.venv/bin/alembic upgrade head

echo "==> Services d'infra prêts. L'API et le frontend démarrent dans les terminaux dédiés."
