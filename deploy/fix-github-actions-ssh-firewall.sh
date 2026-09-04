#!/usr/bin/env bash
# À exécuter SUR le VPS (root) si GitHub Actions ne peut plus joindre le port SSH.
# Ouvre le port 22 via ufw si présent ; le firewall Hostinger (hPanel) reste à configurer manuellement.
set -euo pipefail

SSH_PORT="${SSH_PORT:-22}"

echo "=== Mobility Health — ouverture SSH pour GitHub Actions ==="
echo "Port SSH : ${SSH_PORT}"

if command -v ufw >/dev/null 2>&1; then
  echo "Configuration ufw…"
  ufw allow "${SSH_PORT}/tcp" comment 'SSH deploy GitHub Actions' || true
  ufw status numbered | head -30 || true
else
  echo "ufw absent — configurez le firewall dans hPanel Hostinger :"
  echo "  VPS → Security → Firewall → Add rule → TCP ${SSH_PORT} → Source Anywhere (0.0.0.0/0)"
fi

echo ""
echo "Vérifiez aussi :"
echo "  - VPS démarré (hPanel)"
echo "  - fail2ban : fail2ban-client status sshd  (débannir si besoin)"
echo "  - SSH_HOST GitHub = srv1324425.hstgr.cloud (IP actuelle, pas une ancienne IP figée)"
echo ""
echo "Test depuis votre PC :"
echo "  ssh -4 root@srv1324425.hstgr.cloud hostname"
