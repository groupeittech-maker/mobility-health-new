#!/usr/bin/env bash
# Supprime les conteneurs/réseaux Mobility Health qui bloquent docker compose up
# (conflit de noms fixes : mobility_health_minio, etc.).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-$(dirname "$SCRIPT_DIR")}"
COMPOSE_FILES="${COMPOSE_FILES:--f docker-compose.yml}"

cd "$WORKDIR"

docker_cmd() {
  if [ "$(id -u)" -eq 0 ]; then
    docker "$@"
  elif command -v sudo >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then
    sudo docker "$@"
  elif docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}

echo "🧹 Nettoyage stack Mobility Health (${WORKDIR})..."

# shellcheck disable=SC2086
docker_cmd compose $COMPOSE_FILES stop -t 10 2>/dev/null || true
# shellcheck disable=SC2086
docker_cmd compose $COMPOSE_FILES down -t 10 --remove-orphans 2>/dev/null || true

MHC_CONTAINERS=(
  mobility_health_db
  mobility_health_redis
  mobility_health_minio
  mobility_health_api
  mobility_health_celery_worker
  mobility_health_celery_beat
)

for name in "${MHC_CONTAINERS[@]}"; do
  if docker_cmd ps -a --format '{{.Names}}' | grep -qx "$name"; then
    echo "  → docker rm -f ${name}"
    docker_cmd rm -f "$name" || true
  fi
done

while IFS= read -r cid; do
  [ -n "$cid" ] || continue
  docker_cmd rm -f "$cid" || true
done < <(docker_cmd ps -aq --filter "name=mobility_health" 2>/dev/null || true)

docker_cmd network rm mobility_health_default 2>/dev/null || true

for name in "${MHC_CONTAINERS[@]}"; do
  if docker_cmd ps -a --format '{{.Names}}' | grep -qx "$name"; then
    echo "❌ Conteneur résiduel : ${name}"
    docker_cmd inspect "$name" --format '{{.State.Status}}' 2>/dev/null || true
    exit 1
  fi
done

echo "✅ Nettoyage terminé"
