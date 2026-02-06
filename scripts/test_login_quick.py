#!/usr/bin/env python3
"""
Script de test rapide pour diagnostiquer les problèmes de connexion
"""

import requests
import sys
from datetime import datetime

def test_backend():
    """Tester si le backend répond"""
    print("=" * 60)
    print("TEST DE CONNEXION - Diagnostic rapide")
    print("=" * 60)
    print()
    
    print("1. Test de santé du backend...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("   ✓ Backend accessible")
            print(f"   Réponse: {response.json()}")
        else:
            print(f"   ✗ Backend répond avec le code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ✗ Impossible de se connecter au backend")
        print("   → Le backend n'est probablement pas démarré")
        print("   → Démarrez-le avec: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return False
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        return False
    
    print()
    print("2. Test de l'endpoint de login...")
    try:
        # Test avec des identifiants incorrects pour voir si l'endpoint répond
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            data={"username": "test_invalid", "password": "test_invalid"},
            timeout=5
        )
        if response.status_code in [401, 422]:
            print("   ✓ Endpoint de login accessible")
            try:
                error_data = response.json()
                print(f"   Réponse attendue (401): {error_data.get('detail', 'N/A')}")
            except:
                pass
        else:
            print(f"   ✗ Endpoint répond avec le code {response.status_code}")
            try:
                print(f"   Réponse: {response.text[:200]}")
            except:
                pass
            return False
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        return False
    
    print()
    print("3. Test avec des identifiants valides...")
    username = input("   Nom d'utilisateur: ").strip()
    if not username:
        print("   ✗ Nom d'utilisateur requis")
        return False
    
    password = input("   Mot de passe: ").strip()
    if not password:
        print("   ✗ Mot de passe requis")
        return False
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            data={"username": username, "password": password},
            timeout=10
        )
        
        print(f"   Statut HTTP: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                print("   ✓ Connexion réussie!")
                print(f"   ✓ Token reçu: {data['access_token'][:30]}...")
                print(f"   ✓ Type: {data.get('token_type', 'N/A')}")
                return True
            else:
                print("   ✗ Connexion réussie mais pas de token reçu")
                print(f"   Réponse: {data}")
                return False
        else:
            try:
                error_data = response.json()
                print(f"   ✗ Échec de la connexion")
                print(f"   Détail: {error_data.get('detail', 'Erreur inconnue')}")
            except:
                print(f"   ✗ Échec de la connexion (code {response.status_code})")
                print(f"   Réponse brute: {response.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        print("   ✗ Timeout - Le serveur met trop de temps à répondre")
        return False
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_backend()
    print()
    print("=" * 60)
    if success:
        print("✅ TOUS LES TESTS SONT PASSÉS!")
        print("Le problème est probablement côté frontend.")
        print("Vérifiez:")
        print("  1. Que le frontend est servi via HTTP (pas file://)")
        print("  2. L'URL de l'API dans frontend-simple/js/api.js")
        print("  3. La console du navigateur (F12) pour les erreurs")
    else:
        print("❌ PROBLÈME DÉTECTÉ")
        print("Corrigez les erreurs ci-dessus avant de tester le frontend.")
    print("=" * 60)
    sys.exit(0 if success else 1)

