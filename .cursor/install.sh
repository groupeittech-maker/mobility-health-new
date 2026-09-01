#!/usr/bin/env bash
# Cloud Agent — installation idempotente de l'environnement de développement MHC.
# Exécuté depuis /workspace après le checkout du dépôt.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
APT_OPTS=(-y -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef)

echo "==> [1/5] Paquets système (tesseract, poppler, postgres client, venv, fuse-overlayfs)"
sudo apt-get update -y
sudo apt-get install "${APT_OPTS[@]}" --no-install-recommends \
  tesseract-ocr tesseract-ocr-fra poppler-utils \
  python3-venv python3-dev postgresql-client \
  ca-certificates curl gnupg fuse-overlayfs

echo "==> [2/5] Docker Engine + plugin compose (Postgres/Redis/MinIO tournent en conteneurs)"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sudo sh /tmp/get-docker.sh
fi
# Docker-in-Docker : le montage overlay natif échoue dans la VM imbriquée -> fuse-overlayfs.
sudo mkdir -p /etc/docker
printf '%s\n' '{ "features": { "containerd-snapshotter": false }, "storage-driver": "fuse-overlayfs" }' \
  | sudo tee /etc/docker/daemon.json >/dev/null
sudo usermod -aG docker "$(id -un)" || true

echo "==> [3/5] Environnement virtuel Python + dépendances"
python3 -m venv /workspace/.venv
/workspace/.venv/bin/pip install --upgrade pip
/workspace/.venv/bin/pip install -r apps/mhc/requirements.txt

echo "==> [4/5] Fichier .env de développement (créé seulement s'il est absent)"
if [ ! -f apps/mhc/.env ]; then
  cat > apps/mhc/.env <<'ENVEOF'
# Développement local (Cloud Agent) — généré par .cursor/install.sh, non committé
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/mobility_health
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
LOCAL_FILE_STORAGE_ROOT=/var/lib/mobility-health/uploads
SECRET_KEY=dev-secret-key-for-cloud-agent-only-not-for-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DEBUG=True
ENVIRONMENT=development
PAYMENT_SERVICE_MODE=stub
OCR_SERVICE_MODE=stub
TRUST_SERVICE_MODE=stub
ENVEOF
fi

echo "==> [5/5] Répertoire de stockage local (repli MinIO)"
sudo mkdir -p /var/lib/mobility-health/uploads
sudo chown -R "$(id -un)":"$(id -gn)" /var/lib/mobility-health

echo "==> Installation terminée."
