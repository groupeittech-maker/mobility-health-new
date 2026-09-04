#!/usr/bin/env bash
# Teste la joignabilité SSH depuis un runner GitHub Actions (IPv4).
set -euo pipefail

HOST="${1:?HOST requis}"
PORT="${2:-22}"
MAX_ATTEMPTS="${3:-5}"
WAIT_SECONDS="${4:-15}"

RUNNER_IP="$(curl -sf --max-time 8 https://api.ipify.org 2>/dev/null || curl -sf --max-time 8 https://ifconfig.me 2>/dev/null || echo 'inconnue')"
echo "IP publique du runner GitHub : ${RUNNER_IP}"
echo "Résolution A de ${HOST} :"
getent ahostsv4 "$HOST" | awk '{print $1}' | sort -u || dig +short A "$HOST" || true

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  echo "Test TCP ${HOST}:${PORT} (tentative ${attempt}/${MAX_ATTEMPTS}, timeout 12s)…"
  if timeout 12 bash -c "exec 3<>/dev/tcp/${HOST}/${PORT}" 2>/dev/null; then
    exec 3<&- 3>&- || true
    echo "✅ Port ${PORT} joignable en IPv4 depuis le runner GitHub"
    exit 0
  fi
  if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
    echo "Port ${PORT} injoignable — nouvel essai dans ${WAIT_SECONDS}s…"
    sleep "$WAIT_SECONDS"
  fi
  attempt=$((attempt + 1))
done

echo "::error::Port ${PORT} injoignable après ${MAX_ATTEMPTS} tentatives (Connection timed out)."
echo "Cause probable : firewall Hostinger bloque certaines IP GitHub Actions."
echo "Actions :"
echo "  1. hPanel → VPS → Firewall → autoriser TCP ${PORT} depuis Internet (recommandé avec clé SSH uniquement)"
echo "  2. Ou exécuter sur le VPS : bash deploy/fix-github-actions-ssh-firewall.sh"
echo "  3. IP du runner bloqué : ${RUNNER_IP} (si liste blanche manuelle)"
echo "Doc : docs/CICD-AUTOMATION.md § Deploy SSH"
exit 1
