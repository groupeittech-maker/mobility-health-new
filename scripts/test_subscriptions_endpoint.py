"""
Script de test pour vérifier que l'endpoint /api/v1/subscriptions est accessible
"""
import requests
import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_subscriptions_endpoint(base_url="http://192.168.1.183:8000"):
    """Teste l'endpoint des souscriptions"""
    url = f"{base_url}/api/v1/subscriptions"
    
    print(f"🔍 Test de l'endpoint: {url}")
    print("-" * 60)
    
    try:
        # Test sans authentification (devrait retourner 401)
        print("\n1. Test sans authentification (attendu: 401 Unauthorized)")
        response = requests.get(url, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Endpoint trouvé (401 attendu sans token)")
        elif response.status_code == 404:
            print("   ❌ Endpoint non trouvé (404)")
            print("   ⚠️  Le serveur backend n'a probablement pas rechargé les routes")
            print("   💡 Solution: Redémarrer le serveur backend")
        else:
            print(f"   ⚠️  Status inattendu: {response.status_code}")
            print(f"   Réponse: {response.text[:200]}")
        
        # Test avec un token invalide (devrait retourner 401)
        print("\n2. Test avec token invalide (attendu: 401 Unauthorized)")
        headers = {"Authorization": "Bearer invalid_token"}
        response = requests.get(url, headers=headers, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Endpoint trouvé (401 attendu avec token invalide)")
        elif response.status_code == 404:
            print("   ❌ Endpoint non trouvé (404)")
        else:
            print(f"   ⚠️  Status inattendu: {response.status_code}")
        
        # Vérifier les routes disponibles
        print("\n3. Vérification des routes disponibles")
        root_url = f"{base_url}/api/v1/"
        try:
            response = requests.get(root_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "endpoints" in data:
                    print("   Endpoints disponibles:")
                    for name, path in data["endpoints"].items():
                        marker = "✅" if "subscriptions" in name.lower() else "  "
                        print(f"   {marker} {name}: {path}")
        except Exception as e:
            print(f"   ⚠️  Impossible de récupérer la liste des endpoints: {e}")
        
        print("\n" + "-" * 60)
        print("📋 Résumé:")
        if response.status_code == 404:
            print("   ❌ L'endpoint /api/v1/subscriptions n'est pas disponible")
            print("   💡 Actions recommandées:")
            print("      1. Vérifier que le serveur backend est démarré")
            print("      2. Redémarrer le serveur backend")
            print("      3. Vérifier les logs du serveur pour des erreurs")
        else:
            print("   ✅ L'endpoint est accessible (mais nécessite une authentification)")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Impossible de se connecter au serveur")
        print(f"   💡 Vérifiez que le serveur backend est démarré sur {base_url}")
    except requests.exceptions.Timeout:
        print("   ❌ Timeout - le serveur ne répond pas")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Teste l'endpoint des souscriptions")
    parser.add_argument("--url", default="http://192.168.1.183:8000", help="URL de base du serveur")
    args = parser.parse_args()
    
    test_subscriptions_endpoint(args.url)
