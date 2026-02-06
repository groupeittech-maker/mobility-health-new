#!/bin/bash
# Script pour créer le fichier .env
# Exécutez ce script avec: chmod +x create_env.sh && ./create_env.sh

ENV_CONTENT="# Configuration API - Backend Hostinger (production)
API_BASE_URL=https://srv1324425.hstgr.cloud/api/v1
API_CONNEXION_BACKEND=https://srv1324425.hstgr.cloud
API_TIMEOUT=30000

# Environment (development ou production)
ENVIRONMENT=production

# App Configuration
APP_NAME=Mobility Health
APP_VERSION=1.0.0"

# Créer le fichier .env.example
echo "$ENV_CONTENT" > .env.example

# Créer le fichier .env
if [ ! -f .env ]; then
    echo "$ENV_CONTENT" > .env
    echo "✅ Fichier .env créé avec succès!"
else
    echo "⚠️  Le fichier .env existe déjà."
    read -p "Voulez-vous le remplacer? (O/N) " response
    if [[ "$response" =~ ^[Oo]$ ]]; then
        echo "$ENV_CONTENT" > .env
        echo "✅ Fichier .env mis à jour!"
    fi
fi

echo ""
echo "📝 URL par défaut : backend Hostinger (srv1324425.hstgr.cloud)"
echo "   Pour le développement local, modifiez .env :"
echo "   - Android Emulator: http://10.0.2.2:8000/api/v1"
echo "   - iOS Simulator: http://localhost:8000/api/v1"
echo "   - Appareil physique: http://VOTRE_IP:8000/api/v1"


