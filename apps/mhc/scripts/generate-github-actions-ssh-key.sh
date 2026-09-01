#!/usr/bin/env bash
# Génère une clé SSH dédiée au déploiement GitHub Actions (apps/mhc/deploy-keys/)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MHC_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
KEYS_DIR="${MHC_ROOT}/deploy-keys"
KEY_PATH="${KEYS_DIR}/github_actions_mhc"

mkdir -p "${KEYS_DIR}"

if [[ -f "${KEY_PATH}" ]]; then
  echo "Une clé existe déjà : ${KEY_PATH}"
  echo "Supprimez-la manuellement si vous voulez en regénérer une."
  exit 1
fi

if ! command -v ssh-keygen >/dev/null 2>&1; then
  echo "Erreur: ssh-keygen introuvable."
  exit 1
fi

ssh-keygen -t ed25519 -C "github-actions-mhc" -f "${KEY_PATH}" -N ""

echo ""
echo "Clés créées dans apps/mhc/deploy-keys/"
echo "  Privée → secret GitHub SSH_PRIVATE_KEY : github_actions_mhc"
echo "  Publique → VPS authorized_keys        : github_actions_mhc.pub"
echo ""
echo "Prochaines étapes : voir deploy-keys/README.md"
