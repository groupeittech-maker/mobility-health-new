#!/usr/bin/env bash
# Remise en service du backend + Nginx sur le VPS Mobility Health.
# Usage (sur le serveur) : bash deploy/fix-server-production.sh

set -euo pipefail

BACKEND_DIR="${BACKEND_DIR:-/var/www/Mobility_Health/Mobility_Health}"
FRONTEND_DIR="${FRONTEND_DIR:-/var/www/mobility-health/frontend-simple}"
NGINX_SITE="mobility-health-production.conf"
REPO_NGINX="$(dirname "$0")/nginx/${NGINX_SITE}"

echo "=== Mobility Health — correctif production ==="
echo "Backend : $BACKEND_DIR"
echo ""

if [ ! -d "$BACKEND_DIR" ]; then
  echo "ERREUR: dossier backend introuvable: $BACKEND_DIR"
  exit 1
fi

cd "$BACKEND_DIR"

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
if [ ! -f docker-compose.prod.yml ]; then
  COMPOSE="docker compose -f docker-compose.yml"
fi

echo "[1/6] État Docker avant correction..."
$COMPOSE ps -a || true
echo ""

echo "[2/6] Démarrage des services (db, redis, minio, api, celery)..."
$COMPOSE up -d db redis minio
sleep 5
$COMPOSE up -d api celery_worker celery_beat
echo ""

echo "[3/6] Attente API (port 8000)..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "  OK — API répond sur localhost:8000"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "  ERREUR — API ne répond pas. Logs :"
    $COMPOSE logs api --tail 80
    exit 1
  fi
  sleep 2
done
echo ""

echo "[4/6] Migrations Alembic..."
if $COMPOSE exec -T api alembic upgrade head; then
  echo "  OK — migrations appliquées"
else
  echo "  AVERTISSEMENT — migrations en échec (voir logs ci-dessus)"
fi
echo ""

echo "[5/6] Nginx — configuration production..."
if [ -f "$REPO_NGINX" ]; then
  cp "$REPO_NGINX" "/etc/nginx/sites-available/$NGINX_SITE"
  ln -sf "/etc/nginx/sites-available/$NGINX_SITE" /etc/nginx/sites-enabled/
  # Désactiver d'éventuels doublons conflictuels
  for old in mobility-health.conf default; do
    [ -L "/etc/nginx/sites-enabled/$old" ] && rm -f "/etc/nginx/sites-enabled/$old" && echo "  Désactivé: $old"
  done
  nginx -t
  systemctl reload nginx
  echo "  OK — Nginx rechargé"
else
  echo "  Fichier nginx local absent ($REPO_NGINX), rechargement simple..."
  nginx -t && systemctl reload nginx
fi
echo ""

echo "[6/6] Vérifications finales..."
curl -sf http://127.0.0.1:8000/api/v1/health && echo ""
curl -sfI https://srv1324425.hstgr.cloud/api/v1/health | head -1 || true
curl -sfI https://api.srv1324425.hstgr.cloud/api/v1/health | head -1 || true
echo ""
echo "=== Terminé. Site: https://srv1324425.hstgr.cloud ==="
