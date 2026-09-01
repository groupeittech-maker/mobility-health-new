#!/usr/bin/env python3
"""
Script de diagnostic pour les problèmes de connexion
"""

import requests
import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import verify_password

def test_backend_health():
    """Tester si le backend répond"""
    print("1. Test de santé du backend...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("   ✓ Backend accessible")
            return True
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

def test_login_endpoint():
    """Tester si l'endpoint de login répond"""
    print("\n2. Test de l'endpoint de login...")
    try:
        # Test avec des identifiants incorrects pour voir si l'endpoint répond
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            data={"username": "test_invalid", "password": "test_invalid"},
            timeout=5
        )
        if response.status_code in [401, 422]:
            print("   ✓ Endpoint de login accessible")
            return True
        else:
            print(f"   ✗ Endpoint répond avec le code {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        return False

def check_user_in_db(username):
    """Vérifier si un utilisateur existe dans la base de données"""
    print(f"\n3. Vérification de l'utilisateur '{username}' dans la base de données...")
    db = SessionLocal()
    try:
        # Chercher par username
        user = db.query(User).filter(User.username == username).first()
        if not user:
            # Chercher par email
            user = db.query(User).filter(User.email == username).first()
        
        if user:
            print(f"   ✓ Utilisateur trouvé:")
            print(f"      - ID: {user.id}")
            print(f"      - Username: {user.username}")
            print(f"      - Email: {user.email}")
            print(f"      - Actif: {user.is_active}")
            print(f"      - Rôle: {user.role.value if hasattr(user.role, 'value') else user.role}")
            return user
        else:
            print(f"   ✗ Utilisateur '{username}' non trouvé dans la base de données")
            return None
    except Exception as e:
        print(f"   ✗ Erreur lors de la vérification: {e}")
        return None
    finally:
        db.close()

def test_password(user, password):
    """Tester si le mot de passe est correct"""
    print(f"\n4. Vérification du mot de passe...")
    try:
        if verify_password(password, user.hashed_password):
            print("   ✓ Mot de passe correct")
            return True
        else:
            print("   ✗ Mot de passe incorrect")
            return False
    except Exception as e:
        print(f"   ✗ Erreur lors de la vérification du mot de passe: {e}")
        return False

def test_actual_login(username, password):
    """Tester une vraie connexion"""
    print(f"\n5. Test de connexion avec '{username}'...")
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            data={"username": username, "password": password},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                print("   ✓ Connexion réussie!")
                print(f"   ✓ Token reçu: {data['access_token'][:20]}...")
                return True
            else:
                print("   ✗ Connexion réussie mais pas de token reçu")
                return False
        else:
            try:
                error_data = response.json()
                print(f"   ✗ Échec de la connexion: {error_data.get('detail', 'Erreur inconnue')}")
            except:
                print(f"   ✗ Échec de la connexion (code {response.status_code})")
            return False
    except Exception as e:
        print(f"   ✗ Erreur lors de la connexion: {e}")
        return False

def main():
    print("=" * 60)
    print("DIAGNOSTIC DE CONNEXION - Mobility Health")
    print("=" * 60)
    
    # Demander les identifiants
    username = input("\nNom d'utilisateur ou email: ").strip()
    if not username:
        print("Erreur: Nom d'utilisateur requis")
        sys.exit(1)
    
    password = input("Mot de passe: ").strip()
    if not password:
        print("Erreur: Mot de passe requis")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC EN COURS...")
    print("=" * 60)
    
    # Tests
    backend_ok = test_backend_health()
    if not backend_ok:
        print("\n❌ Le backend n'est pas accessible. Démarrez-le d'abord.")
        sys.exit(1)
    
    login_endpoint_ok = test_login_endpoint()
    if not login_endpoint_ok:
        print("\n❌ L'endpoint de login ne répond pas correctement.")
        sys.exit(1)
    
    user = check_user_in_db(username)
    if not user:
        print("\n❌ L'utilisateur n'existe pas dans la base de données.")
        print("   → Créez l'utilisateur avec: python scripts/create_test_users.py")
        sys.exit(1)
    
    if not user.is_active:
        print("\n❌ Le compte utilisateur est désactivé.")
        print("   → Réactivez-le avec: python scripts/fix_user_login.py")
        sys.exit(1)
    
    password_ok = test_password(user, password)
    if not password_ok:
        print("\n❌ Le mot de passe est incorrect.")
        print("   → Réinitialisez-le avec: python scripts/fix_user_login.py")
        sys.exit(1)
    
    login_ok = test_actual_login(username, password)
    if not login_ok:
        print("\n❌ La connexion échoue malgré des identifiants valides.")
        print("   → Vérifiez les logs du backend pour plus de détails.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ TOUS LES TESTS SONT PASSÉS!")
    print("=" * 60)
    print("\nLe problème est probablement côté frontend:")
    print("  1. Vérifiez que le frontend est servi via HTTP (pas file://)")
    print("  2. Vérifiez l'URL de l'API dans frontend-simple/js/api.js")
    print("  3. Ouvrez la console du navigateur (F12) pour voir les erreurs")
    print("  4. Vérifiez les erreurs CORS dans l'onglet Network")

if __name__ == "__main__":
    main()

