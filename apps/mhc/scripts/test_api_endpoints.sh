#!/bin/bash
# Test rapide des endpoints API (à lancer sur le VPS ou en local)
# Usage: ./scripts/test_api_endpoints.sh [BASE_URL]
# Ex: ./scripts/test_api_endpoints.sh https://srv1324425.hstgr.cloud

BASE_URL="${1:-http://localhost:8000}"

echo "=== Mobility Health API - Tests ==="
echo "Base URL: $BASE_URL"
echo ""

echo "1. Health..."
curl -s "$BASE_URL/health" | head -c 200
echo ""
echo ""

echo "2. OpenAPI JSON (premiers octets)..."
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/openapi.json"
echo " (attendu: 200)"
echo ""

echo "3. Docs (code HTTP)..."
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/docs"
echo " (attendu: 200)"
echo ""

echo "4. Login (nécessite un utilisateur existant)..."
CODE=$(curl -s -o /tmp/login.json -w "%{http_code}" -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@mobilityhealth.com&password=admin")
echo "HTTP $CODE"
if [ "$CODE" = "200" ]; then
  echo "Token présent: $(grep -o '"access_token":"[^"]*"' /tmp/login.json | head -c 50)..."
else
  cat /tmp/login.json 2>/dev/null | head -c 300
fi
echo ""
echo "=== Fin des tests ==="
