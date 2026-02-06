"""
Script pour tester la connexion avec l'utilisateur 'user'
Usage: python scripts/test_login.py
"""
import sys
import os
import requests

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_login():
    """Tester la connexion avec l'utilisateur 'user'"""
    base_url = "http://localhost:8000/api/v1"
    login_url = f"{base_url}/auth/login"
    
    print("=" * 60)
    print("Test de connexion - Utilisateur 'user'")
    print("=" * 60)
    print()
    
    # Test 1: Vérifier que le serveur est accessible
    print("1. Vérification de l'accessibilité du serveur...")
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code == 200:
            print("   ✓ Serveur accessible")
        else:
            print(f"   ✗ Serveur répond avec le code {health_response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ✗ Impossible de se connecter au serveur")
        print("   → Vérifiez que le backend est démarré sur http://localhost:8000")
        return False
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        return False
    
    # Test 2: Tester la connexion avec user/user123
    print("\n2. Test de connexion avec user/user123...")
    try:
        login_data = {
            "username": "user",
            "password": "user123"
        }
        
        response = requests.post(
            login_url,
            data=login_data,  # Utiliser data= pour FormData (OAuth2PasswordRequestForm)
            timeout=10
        )
        
        print(f"   Code de statut: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                print("   ✓ Connexion réussie !")
                print(f"   ✓ Token reçu: {data['access_token'][:50]}...")
                print(f"   ✓ Type de token: {data.get('token_type', 'N/A')}")
                
                # Test 3: Vérifier que le token fonctionne
                print("\n3. Vérification du token...")
                me_url = f"{base_url}/auth/me"
                headers = {
                    "Authorization": f"Bearer {data['access_token']}"
                }
                me_response = requests.get(me_url, headers=headers, timeout=5)
                
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    print("   ✓ Token valide")
                    print(f"   ✓ Utilisateur: {user_data.get('username', 'N/A')}")
                    print(f"   ✓ Email: {user_data.get('email', 'N/A')}")
                    print(f"   ✓ Rôle: {user_data.get('role', 'N/A')}")
                    print(f"   ✓ Actif: {user_data.get('is_active', 'N/A')}")
                else:
                    print(f"   ✗ Erreur lors de la vérification du token: {me_response.status_code}")
                    print(f"   Réponse: {me_response.text}")
                
                return True
            else:
                print("   ✗ Token d'accès non reçu dans la réponse")
                print(f"   Réponse: {data}")
                return False
        else:
            print(f"   ✗ Échec de la connexion")
            try:
                error_data = response.json()
                print(f"   Détail: {error_data.get('detail', 'Erreur inconnue')}")
            except:
                print(f"   Réponse brute: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ✗ Timeout - Le serveur met trop de temps à répondre")
        return False
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        return False


if __name__ == "__main__":
    success = test_login()
    
    print()
    print("=" * 60)
    if success:
        print("✅ Tous les tests sont passés avec succès")
        print("\n💡 Si la connexion ne fonctionne pas dans le navigateur,")
        print("   vérifiez:")
        print("   1. Que vous utilisez un serveur HTTP (pas file://)")
        print("   2. La console du navigateur pour les erreurs")
        print("   3. Que CORS est configuré correctement")
    else:
        print("✗ Des erreurs ont été détectées")
        print("\n💡 Solutions possibles:")
        print("   1. Démarrer le backend: uvicorn app.main:app --reload")
        print("   2. Vérifier que la base de données est accessible")
        print("   3. Exécuter: python scripts/fix_user_login.py")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

