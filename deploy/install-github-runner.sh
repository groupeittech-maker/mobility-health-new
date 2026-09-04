#!/usr/bin/env bash
# Installe un runner GitHub Actions sur le VPS Hostinger (une seule fois).
# À lancer DEPUIS LE VPS (ssh root@srv1324425.hstgr.cloud), pas depuis GitHub cloud.
#
# Usage :
#   curl -fsSL https://raw.githubusercontent.com/groupeittech-maker/mobility-health-new/main/deploy/install-github-runner.sh | bash
#   # ou après clone :
#   bash deploy/install-github-runner.sh
#
# Puis dans GitHub : Settings → Secrets and variables → Actions → Variables
#   USE_SELF_HOSTED_DEPLOY = true
set -euo pipefail

RUNNER_USER="${RUNNER_USER:-deployer}"
RUNNER_DIR="${RUNNER_DIR:-/opt/actions-runner-mhc}"
REPO_URL="${REPO_URL:-https://github.com/groupeittech-maker/mobility-health-new}"
RUNNER_VERSION="${RUNNER_VERSION:-2.321.0}"
LABELS="${LABELS:-self-hosted,Linux,X64,mhc-vps}"

echo "=== Installation runner GitHub Actions — Mobility Health ==="
echo "Utilisateur : $RUNNER_USER"
echo "Répertoire  : $RUNNER_DIR"
echo "Labels      : $LABELS"
echo ""

if [ "$(id -u)" -ne 0 ]; then
  echo "Relancez en root : sudo bash $0"
  exit 1
fi

if ! id "$RUNNER_USER" >/dev/null 2>&1; then
  echo "Création utilisateur $RUNNER_USER…"
  useradd -m -s /bin/bash "$RUNNER_USER"
fi

if ! command -v docker >/dev/null; then
  echo "⚠️  Docker non trouvé — le déploiement backend en aura besoin."
fi

# Token d'enregistrement (valide ~1 h) : GitHub → Settings → Actions → Runners → New self-hosted runner
if [ -z "${RUNNER_TOKEN:-}" ]; then
  echo ""
  echo "Obtenez un token d'enregistrement :"
  echo "  GitHub → groupeittech-maker/mobility-health-new → Settings → Actions → Runners"
  echo "  → New self-hosted runner → Linux → copiez le token"
  echo ""
  read -r -p "Collez le token RUNNER_TOKEN : " RUNNER_TOKEN
fi

if [ -z "$RUNNER_TOKEN" ]; then
  echo "Token requis."
  exit 1
fi

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

if [ ! -f ./config.sh ]; then
  echo "Téléchargement actions-runner v${RUNNER_VERSION}…"
  curl -fsSL -o actions-runner.tar.gz \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
  tar xzf actions-runner.tar.gz
  rm -f actions-runner.tar.gz
fi

chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"

echo "Configuration du runner…"
sudo -u "$RUNNER_USER" ./config.sh \
  --url "$REPO_URL" \
  --token "$RUNNER_TOKEN" \
  --name "mhc-vps-$(hostname -s)" \
  --labels "$LABELS" \
  --unattended \
  --replace

echo "Installation service systemd…"
./svc.sh install "$RUNNER_USER"
./svc.sh start
./svc.sh status || true

echo ""
echo "✅ Runner installé."
echo ""
echo "Étapes GitHub (obligatoire) :"
echo "  1. Settings → Secrets and variables → Actions → Variables"
echo "  2. New repository variable : USE_SELF_HOSTED_DEPLOY = true"
echo "  3. Relancer : Actions → Deploy to Hostinger VPS"
echo ""
echo "Le job utilisera le runner sur ce VPS (plus besoin d'ouvrir le port 22 aux IP GitHub)."
