#!/usr/bin/env bash
# Déploiement complet frontend + backend via SSH (runner GitHub cloud).
set -euo pipefail

REPO_ROOT="${GITHUB_WORKSPACE:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$REPO_ROOT"

echo "📦 Archives frontend / backend…"
tar czf frontend.tar.gz -C apps/mhc/frontend-simple .
test -s frontend.tar.gz
tar czf app.tar.gz --exclude="__pycache__" --exclude="*.pyc" --exclude="*.pyo" --exclude=".git" -C apps/mhc app/
tar czf alembic.tar.gz --exclude="__pycache__" --exclude="*.pyc" --exclude=".git" -C apps/mhc alembic/
cp apps/mhc/docker-compose.yml .
cp apps/mhc/docker-compose.prod.yml .
cp apps/mhc/Dockerfile .
cp apps/mhc/Dockerfile.prod .
cp apps/mhc/requirements.txt .
cp apps/mhc/alembic.ini .

scp -4 frontend.tar.gz mhc-vps:/tmp/frontend.tar.gz
scp -4 app.tar.gz alembic.tar.gz docker-compose.yml docker-compose.prod.yml \
  Dockerfile Dockerfile.prod requirements.txt alembic.ini \
  mhc-vps:/tmp/

ssh -4 mhc-vps "bash -s" < .github/scripts/remote-deploy-frontend.sh

if [ -n "${SMTP_PASSWORD:-}" ]; then
  scp -4 .github/scripts/configure-smtp-env.sh mhc-vps:/tmp/configure-smtp-env.sh
  ssh -4 mhc-vps "SMTP_PASSWORD='$SMTP_PASSWORD' SMTP_USER='noreply@mobility-healthcare.cloud' SMTP_FROM_EMAIL='noreply@mobility-healthcare.cloud' ASSURANCE_EMAIL='noreply@mobility-healthcare.cloud' bash /tmp/configure-smtp-env.sh"
else
  echo "⚠️ SMTP_PASSWORD absent — .env SMTP inchangé"
fi

ssh -4 mhc-vps "bash -s" < .github/scripts/remote-deploy-backend.sh
echo "✅ Déploiement SSH terminé"
