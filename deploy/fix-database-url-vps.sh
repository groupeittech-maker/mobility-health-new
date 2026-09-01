#!/bin/bash
# Force DATABASE_URL Docker (@db:5432) sur le VPS.
# Usage : bash deploy/fix-database-url-vps.sh

set -euo pipefail
cd /var/www/Mobility_Health/Mobility_Health
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

echo "=== Avant correction ==="
grep -E '^(DATABASE_URL|POSTGRES_HOST|POSTGRES_PORT)=' .env 2>/dev/null || true
$COMPOSE config 2>/dev/null | grep DATABASE_URL || true

PU="${POSTGRES_USER:-postgres}"
PP="${POSTGRES_PASSWORD:-postgres}"
PD="${POSTGRES_DB:-mobility_health}"
[ -f .env ] && PU=$(grep -m1 '^POSTGRES_USER=' .env | cut -d= -f2- || echo postgres)
[ -f .env ] && PP=$(grep -m1 '^POSTGRES_PASSWORD=' .env | cut -d= -f2- || echo postgres)
[ -f .env ] && PD=$(grep -m1 '^POSTGRES_DB=' .env | cut -d= -f2- || echo mobility_health)

# Retirer les lignes qui forcent localhost / 127.0.0.1
[ -f .env ] && grep -v -E '^(DATABASE_URL|POSTGRES_HOST|POSTGRES_PORT)=' .env > .env.tmp && mv .env.tmp .env

cat >> .env <<EOF
DATABASE_URL=postgresql://${PU}:${PP}@db:5432/${PD}
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
EOF

echo ""
echo "=== .env corrigé ==="
grep -E '^(DATABASE_URL|REDIS_URL|MINIO_ENDPOINT)=' .env

echo ""
echo "=== Recréation des conteneurs (env frais) ==="
sudo $COMPOSE up -d --force-recreate api celery_worker celery_beat

sleep 15
echo ""
echo "=== DATABASE_URL dans le conteneur ==="
sudo $COMPOSE exec -T api printenv DATABASE_URL

echo ""
echo "=== Migrations ==="
sudo $COMPOSE exec -T api alembic upgrade head

echo ""
echo "=== Test produits ==="
curl -sf http://localhost:8000/api/v1/products | head -c 400
echo ""
