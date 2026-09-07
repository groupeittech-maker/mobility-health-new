#!/usr/bin/env bash
# Met à jour SMTP dans apps/mhc/.env sur le VPS (runner self-hosted ou SSH manuel).
set -euo pipefail

ENV_FILE="${ENV_FILE:-/var/www/Mobility_Health/Mobility_Health/.env}"
SMTP_DOMAIN="${SMTP_DOMAIN:-mobility-healthcare.cloud}"
SMTP_USER="${SMTP_USER:-noreply@${SMTP_DOMAIN}}"
SMTP_FROM="${SMTP_FROM_EMAIL:-${SMTP_USER}}"
ASSURANCE_EMAIL="${ASSURANCE_EMAIL:-contact@${SMTP_DOMAIN}}"
SMTP_HOST="${SMTP_HOST:-smtp.hostinger.com}"
SMTP_PORT="${SMTP_PORT:-465}"
SMTP_SECURITY="${SMTP_SECURITY:-ssl}"
SMTP_FROM_NAME="${SMTP_FROM_NAME:-Mobility HealthCare}"

if [ -z "${SMTP_PASSWORD:-}" ]; then
  echo "::error::SMTP_PASSWORD est requis (secret GitHub ou variable d'environnement)."
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "::error::Fichier .env introuvable : $ENV_FILE"
  exit 1
fi

upsert_env() {
  local key="$1"
  local value="$2"
  local escaped
  escaped="$(printf '%s' "$value" | sed 's/[\\&|]/\\&/g')"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${escaped}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi
}

upsert_env "SMTP_HOST" "$SMTP_HOST"
upsert_env "SMTP_PORT" "$SMTP_PORT"
upsert_env "SMTP_SECURITY" "$SMTP_SECURITY"
upsert_env "SMTP_USER" "$SMTP_USER"
upsert_env "SMTP_PASSWORD" "$SMTP_PASSWORD"
upsert_env "SMTP_FROM_EMAIL" "$SMTP_FROM"
upsert_env "SMTP_FROM_NAME" "$SMTP_FROM_NAME"
upsert_env "ASSURANCE_EMAIL" "$ASSURANCE_EMAIL"

echo "✅ SMTP configuré dans $ENV_FILE"
echo "   SMTP_USER=$SMTP_USER"
echo "   SMTP_FROM_EMAIL=$SMTP_FROM"
echo "   ASSURANCE_EMAIL=$ASSURANCE_EMAIL"

COMPOSE_FILES="-f docker-compose.yml"
[ -f "$(dirname "$ENV_FILE")/docker-compose.prod.yml" ] && COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.prod.yml"

cd "$(dirname "$ENV_FILE")"
echo "🔄 Redémarrage api + celery_worker…"
sudo docker compose $COMPOSE_FILES restart api celery_worker celery_beat 2>/dev/null || \
  sudo docker compose $COMPOSE_FILES restart api celery_worker 2>/dev/null || true

sleep 12
echo "🧪 Test /api/v1/health/email …"
curl -sf "https://srv1324425.hstgr.cloud/api/v1/health/email" | head -c 800 || true
echo ""
