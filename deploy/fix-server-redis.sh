#!/bin/bash
# Corrige le conflit Redis (port 6379) et redémarre toute la stack Mobility Health.
# Usage sur le VPS :
#   bash /var/www/Mobility_Health/Mobility_Health/deploy/fix-server-redis.sh

set -euo pipefail

PROJECT_DIR="/var/www/Mobility_Health/Mobility_Health"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

cd "$PROJECT_DIR"

echo "=== 1. Processus sur le port 6379 ==="
ss -tlnp | grep 6379 || echo "(aucun processus détecté sur 6379)"

echo ""
echo "=== 2. Arrêt du Redis système (hors Docker) s'il existe ==="
for svc in redis-server redis; do
  if systemctl is-active --quiet "$svc" 2>/dev/null; then
    echo "Arrêt de $svc..."
    systemctl stop "$svc"
    systemctl disable "$svc" || true
  fi
done

echo ""
echo "=== 3. Correction DATABASE_URL (.env) pour Docker interne ==="
if [ -f .env ]; then
  sed -i 's|@127.0.0.1:5433|@db:5432|g' .env
  sed -i 's|@localhost:5433|@db:5432|g' .env
  sed -i 's|redis://localhost:6379|redis://redis:6379|g' .env
  sed -i 's|MINIO_ENDPOINT=localhost:9000|MINIO_ENDPOINT=minio:9000|g' .env
  grep -E '^(DATABASE_URL|REDIS_URL|MINIO_ENDPOINT)=' .env || true
fi

echo ""
echo "=== 4. Rebuild API (sans .env dans l'image) ==="
sudo $COMPOSE build --no-cache api celery_worker celery_beat

echo ""
echo "=== 5. Redémarrage de la stack Docker ==="
sudo $COMPOSE down || true
sudo $COMPOSE up -d

echo ""
echo "=== 6. Attente santé des services (25 s) ==="
sleep 25

echo ""
echo "=== 7. État des conteneurs ==="
sudo $COMPOSE ps

echo ""
echo "=== 8. DATABASE_URL dans le conteneur API ==="
sudo $COMPOSE exec -T api printenv DATABASE_URL || true

echo ""
echo "=== 9. Migrations Alembic ==="
sudo $COMPOSE exec -T api alembic upgrade head

echo ""
echo "=== 10. Tests API ==="
curl -sf http://localhost:8000/health && echo ""
curl -sf http://localhost:8000/api/v1/products | head -c 400 && echo ""

echo ""
echo "=== Terminé ==="
