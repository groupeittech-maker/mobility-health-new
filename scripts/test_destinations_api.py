"""
Script pour tester les endpoints de destinations
"""
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_destinations_endpoints():
    """Tester les endpoints de destinations"""
    base_url = "http://localhost:8000/api/v1"
    
    print("=" * 60)
    print("TEST DES ENDPOINTS DE DESTINATIONS")
    print("=" * 60)
    
    # Test 1: Endpoint public (nécessite authentification)
    print("\n1️⃣  Test GET /destinations/countries (public, nécessite auth)")
    try:
        response = requests.get(f"{base_url}/destinations/countries", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Endpoint existe (401 = non authentifié, c'est normal)")
        elif response.status_code == 200:
            print("   ✅ Endpoint fonctionne")
        else:
            print(f"   ⚠️  Status inattendu: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Serveur non accessible")
        return
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # Test 2: Endpoint admin
    print("\n2️⃣  Test GET /destinations/admin/countries (admin)")
    try:
        response = requests.get(f"{base_url}/destinations/admin/countries", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Endpoint existe (401 = non authentifié, c'est normal)")
        elif response.status_code == 403:
            print("   ✅ Endpoint existe (403 = pas admin, c'est normal)")
        elif response.status_code == 404:
            print("   ❌ Endpoint non trouvé (404) - Le serveur n'a peut-être pas été redémarré")
        else:
            print(f"   ⚠️  Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # Test 3: Vérifier la documentation
    print("\n3️⃣  Test GET /docs (documentation Swagger)")
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Documentation accessible")
            print("   💡 Ouvrez http://localhost:8000/docs pour voir toutes les routes")
        else:
            print(f"   ⚠️  Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    print("\n" + "=" * 60)
    print("💡 Si vous voyez des erreurs 404, redémarrez le serveur:")
    print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("=" * 60)

if __name__ == "__main__":
    test_destinations_endpoints()

