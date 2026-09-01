"""
Script pour tester la connexion admin directement via l'API
"""
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_admin_login():
    """Tester la connexion admin via l'API"""
    api_url = os.getenv('API_BASE_URL', 'http://localhost:8000/api/v1')
    login_url = f"{api_url}/auth/login"
    
    print(f"🔍 Test de connexion admin")
    print(f"   URL: {login_url}")
    print(f"   Username: admin")
    print(f"   Password: admin123")
    print()
    
    # Préparer les données de connexion
    form_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    try:
        print("📤 Envoi de la requête de connexion...")
        response = requests.post(
            login_url,
            data=form_data,
            timeout=10
        )
        
        print(f"📥 Réponse reçue:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Connexion réussie !")
            print(f"   Access Token: {data.get('access_token', 'N/A')[:50]}...")
            print(f"   Token Type: {data.get('token_type', 'N/A')}")
            print(f"   Refresh Token: {data.get('refresh_token', 'N/A')[:50]}...")
            return True
        else:
            try:
                error_data = response.json()
                print(f"❌ Erreur de connexion:")
                print(f"   Detail: {error_data.get('detail', 'Erreur inconnue')}")
            except:
                print(f"❌ Erreur HTTP {response.status_code}")
                print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Impossible de se connecter à l'API")
        print(f"   Vérifiez que le serveur est démarré sur {api_url}")
        print(f"   Commande: uvicorn app.main:app --reload")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Timeout lors de la connexion à l'API")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

if __name__ == "__main__":
    test_admin_login()

