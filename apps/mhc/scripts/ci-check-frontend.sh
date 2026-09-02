#!/usr/bin/env bash
# Vérifications charte graphique frontend-simple (CI).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FE="$ROOT/frontend-simple"
CSS="$FE/css/style.css"

echo "== Frontend charte graphique =="

required_assets=(
  "$FE/assets/wallpaper-brand.jpg"
  "$FE/assets/logo_officiel_mh.jpg"
  "$FE/assets/logo_officiel_mh.png"
  "$FE/assets/card-pattern-purple.png"
  "$FE/assets/card-pattern-teal.png"
)

for asset in "${required_assets[@]}"; do
  if [[ ! -f "$asset" ]]; then
    echo "❌ Asset manquant : $asset"
    exit 1
  fi
  echo "✅ $(basename "$asset")"
done

grep -q '#4e267c' "$CSS" || { echo "❌ Couleur brand violet absente de style.css"; exit 1; }
grep -q '#14AE98' "$CSS" || { echo "❌ Couleur brand teal absente de style.css"; exit 1; }
grep -q 'wallpaper-brand.jpg' "$CSS" || { echo "❌ Wallpaper non référencé dans style.css"; exit 1; }
grep -q 'text-highlight' "$CSS" || { echo "❌ Classes text-highlight absentes de style.css"; exit 1; }
echo "✅ Couleurs, wallpaper et classes text-highlight (sans fond)"

# Pages clés référencent le CSS partagé
for page in index.html login.html register.html; do
  if ! grep -q 'css/style.css' "$FE/$page"; then
    echo "❌ $page ne charge pas css/style.css"
    exit 1
  fi
  echo "✅ $page → style.css"
done

echo "== Frontend OK =="
