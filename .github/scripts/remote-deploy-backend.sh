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

echo "[1/6] 🔨 Rebuilding Docker images..."
sudo docker compose build --no-cache api

echo "[2/6] 🛑 Stopping existing services..."
sudo docker compose down --remove-orphans || true
sudo docker ps -a --filter "name=mobility_health" --format "{{.ID}}" | xargs -r sudo docker rm -f || true
if command -v lsof >/dev/null && sudo lsof -ti:9000 >/dev/null 2>&1; then
  echo "⚠️ Port 9000 is in use, freeing it..."
  sudo lsof -ti:9000 | xargs -r sudo kill -9 || true
  sleep 2
fi

echo "[3/6] 🚀 Starting all services..."
sudo docker compose up -d

echo "[4/6] ⏳ Waiting for services..."
sleep 20
sudo docker compose ps
sudo docker compose exec -T db pg_isready -U postgres || true

echo "[5/6] 📊 Running database migrations..."
sudo docker compose exec -T api alembic current || true
sudo docker compose exec -T api alembic upgrade head

echo "[6/6] 🔄 Restarting API..."
sudo docker compose restart api
sudo docker compose ps
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
      sudo docker compose logs api --tail 50 || true
      exit 1
    fi
  fi
done

echo "✅ Backend deployment completed successfully!"
