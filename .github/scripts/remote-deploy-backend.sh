#!/usr/bin/env bash
set -euo pipefail
cd /var/www/Mobility_Health/Mobility_Health

echo "🔧 Fixing permissions..."
if [ -d /var/www/mobility-health/backend ] && id deployer >/dev/null 2>&1; then
  sudo chown -R deployer:deployer /var/www/mobility-health/backend || true
fi

echo "📦 Extracting backend files..."
if [ -f "/tmp/app.tar.gz" ]; then
  sudo rm -rf app
  sudo tar xzf /tmp/app.tar.gz
  if id deployer >/dev/null 2>&1; then sudo chown -R deployer:deployer app; fi
  rm /tmp/app.tar.gz
  echo "✅ App directory extracted"
else
  echo "❌ app.tar.gz not found!"
  exit 1
fi

if [ -f "/tmp/alembic.tar.gz" ]; then
  sudo rm -rf alembic
  sudo tar xzf /tmp/alembic.tar.gz
  if id deployer >/dev/null 2>&1; then sudo chown -R deployer:deployer alembic; fi
  rm /tmp/alembic.tar.gz
  echo "✅ Alembic directory extracted"
else
  echo "❌ alembic.tar.gz not found!"
  exit 1
fi

copy_tmp() {
  local src="$1" dest="$2"
  if [ -f "/tmp/${src}" ]; then
    sudo cp "/tmp/${src}" "${dest}"
    if id deployer >/dev/null 2>&1; then sudo chown deployer:deployer "${dest}"; fi
    rm "/tmp/${src}"
    echo "✅ ${src} copied"
  fi
}

copy_tmp docker-compose.yml docker-compose.yml
copy_tmp Dockerfile Dockerfile
copy_tmp Dockerfile.prod Dockerfile.prod
copy_tmp docker-compose.prod.yml docker-compose.prod.yml
copy_tmp requirements.txt requirements.txt
copy_tmp alembic.ini alembic.ini

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
if [ ! -f docker-compose.prod.yml ]; then
  COMPOSE_FILES="-f docker-compose.yml"
fi

stop_system_redis() {
  for svc in redis-server redis; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      echo "⚠️ Arrêt du Redis système ($svc) pour libérer le port 6379..."
      sudo systemctl stop "$svc" || true
      sudo systemctl disable "$svc" || true
    fi
  done
}

free_port() {
  local port="$1"
  sudo docker ps -q --filter "publish=${port}" | xargs -r sudo docker stop || true
  sudo docker ps -aq --filter "publish=${port}" | xargs -r sudo docker rm -f || true
  if command -v lsof >/dev/null && sudo lsof -ti:"${port}" >/dev/null 2>&1; then
    echo "⚠️ Port ${port} occupé, libération..."
    sudo lsof -ti:"${port}" | xargs -r sudo kill -9 || true
    sleep 2
  fi
}

cleanup_mhc_stack() {
  echo "🧹 Nettoyage complet de la stack Mobility Health..."
  sudo docker compose $COMPOSE_FILES stop -t 15 2>/dev/null || true
  sudo docker compose $COMPOSE_FILES down -t 15 --remove-orphans 2>/dev/null || true

  local names=(
    mobility_health_db
    mobility_health_redis
    mobility_health_minio
    mobility_health_api
    mobility_health_celery_worker
    mobility_health_celery_beat
  )
  for name in "${names[@]}"; do
    if sudo docker container inspect "$name" >/dev/null 2>&1; then
      echo "  Suppression forcée du conteneur ${name}..."
      sudo docker rm -f "$name" || true
    fi
  done

  sudo docker ps -aq --filter "name=mobility_health" | xargs -r sudo docker rm -f || true
  sudo docker network rm mobility_health_default 2>/dev/null || true
  sleep 2
}

if [ -f .env ]; then
  sed -i 's|@127.0.0.1:5433|@db:5432|g' .env || true
  sed -i 's|@localhost:5433|@db:5432|g' .env || true
  sed -i 's|redis://localhost:6379|redis://redis:6379|g' .env || true
  sed -i 's|MINIO_ENDPOINT=localhost:9000|MINIO_ENDPOINT=minio:9000|g' .env || true
fi

echo "[1/6] 🔨 Rebuilding Docker images..."
sudo docker compose $COMPOSE_FILES build --no-cache api celery_worker celery_beat

echo "[2/6] 🛑 Stopping existing services..."
stop_system_redis
cleanup_mhc_stack
for port in 6379 5433 8000 9000 9001; do
  free_port "$port"
done
cleanup_mhc_stack

echo "[3/6] 🚀 Starting all services..."
sudo docker compose $COMPOSE_FILES up -d --force-recreate --remove-orphans

echo "[4/6] ⏳ Waiting for services..."
sleep 20
sudo docker compose $COMPOSE_FILES ps
sudo docker compose $COMPOSE_FILES exec -T db pg_isready -U postgres || true

echo "[5/6] 📊 Running database migrations..."
sudo docker compose $COMPOSE_FILES exec -T api alembic current || true
sudo docker compose $COMPOSE_FILES exec -T api alembic upgrade head

echo "[6/6] 🔄 Restarting API..."
sudo docker compose $COMPOSE_FILES restart api
sudo docker compose $COMPOSE_FILES ps
sudo systemctl reload nginx || true

echo "🧪 Testing API health..."
sleep 15
MAX_RETRIES=3
RETRY_COUNT=0
API_HEALTHY=false
while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$API_HEALTHY" = false ]; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if curl -f -s https://srv1324425.hstgr.cloud/health >/dev/null 2>&1; then
    API_HEALTHY=true
    echo "✅ API health check passed (attempt $RETRY_COUNT/$MAX_RETRIES)"
    curl -s https://srv1324425.hstgr.cloud/health | head -n 5
  else
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
      echo "⚠️ API health check failed (attempt $RETRY_COUNT/$MAX_RETRIES), retrying..."
      sleep 5
    else
      echo "❌ API health check failed after $MAX_RETRIES attempts"
      sudo docker compose $COMPOSE_FILES logs api --tail 50 || true
      exit 1
    fi
  fi
done

echo "✅ Backend deployment completed successfully!"
