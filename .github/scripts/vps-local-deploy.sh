#!/usr/bin/env bash
# Déploiement local sur le VPS — exécuté par le runner GitHub self-hosted (pas de SSH entrant).
set -euo pipefail

REPO_ROOT="${GITHUB_WORKSPACE:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$REPO_ROOT"

echo "=== Déploiement local VPS (self-hosted runner) ==="
echo "Commit : ${GITHUB_SHA:-local}"
echo "Workspace : $REPO_ROOT"

echo "📦 Archives frontend / backend…"
tar czf /tmp/frontend.tar.gz -C apps/mhc/frontend-simple .
tar czf /tmp/app.tar.gz --exclude="__pycache__" --exclude="*.pyc" --exclude="*.pyo" --exclude=".git" -C apps/mhc app/
tar czf /tmp/alembic.tar.gz --exclude="__pycache__" --exclude="*.pyc" --exclude=".git" -C apps/mhc alembic/
cp apps/mhc/docker-compose.yml /tmp/docker-compose.yml
cp apps/mhc/docker-compose.prod.yml /tmp/docker-compose.prod.yml
cp apps/mhc/Dockerfile /tmp/Dockerfile
cp apps/mhc/Dockerfile.prod /tmp/Dockerfile.prod
cp apps/mhc/requirements.txt /tmp/requirements.txt
cp apps/mhc/alembic.ini /tmp/alembic.ini

echo "🚀 Frontend…"
bash .github/scripts/remote-deploy-frontend.sh

echo "🚀 Backend…"
bash .github/scripts/remote-deploy-backend.sh

echo "✅ Déploiement local terminé"
