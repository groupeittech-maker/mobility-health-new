#!/bin/bash
# Script to create test users
# Usage: ./scripts/create_test_users.sh

echo "Création des utilisateurs de test..."

python scripts/create_test_users.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Script exécuté avec succès!"
else
    echo ""
    echo "❌ Erreur lors de l'exécution du script"
    exit 1
fi

