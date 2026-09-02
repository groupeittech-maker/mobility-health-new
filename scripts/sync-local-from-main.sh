#!/usr/bin/env bash
# Synchronise le dépôt local avec main après un déploiement CI/CD.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== Sync local ← origin/main =="
git fetch origin main

CURRENT="$(git branch --show-current)"
if [ "$CURRENT" != "main" ]; then
  echo "Branche actuelle : $CURRENT → bascule sur main"
  git checkout main
fi

git pull --ff-only origin main
SHA="$(git rev-parse --short HEAD)"
echo "✅ Local à jour avec main ($SHA)"
echo ""
echo "Dernier workflow Deploy : https://github.com/$(git remote get-url origin | sed -E 's|.*github.com[:/](.+)(\.git)?|\1|')/actions/workflows/deploy.yml"
