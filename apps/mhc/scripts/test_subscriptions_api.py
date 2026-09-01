"""
Script pour tester l'endpoint /api/v1/subscriptions
"""
import requests
import sys
import json

def test_subscriptions_endpoint(base_url="http://192.168.1.183:8000", token=None):
    """Teste l'endpoint des souscriptions avec authentification"""
    url = f"{base_url}/api/v1/subscriptions"
    
    print(f"🔍 Test de l'endpoint: {url}")
    print("-" * 60)
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
        print(f"🔑 Utilisation du token: {token[:20]}...")
    else:
        print("⚠️  Aucun token fourni - test sans authentification")
    
    try:
        print("\n📡 Envoi de la requête GET...")
        response = requests.get(
            url,
            headers=headers,
            params={"skip": 0, "limit": 1000},
            timeout=10
        )
        
        print(f"📥 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Succès! {len(data)} souscription(s) trouvée(s)")
            print("\n📋 Détails des souscriptions:")
            for i, sub in enumerate(data, 1):
                print(f"\n   Souscription {i}:")
                print(f"   - ID: {sub.get('id')}")
                print(f"   - Numéro: {sub.get('numero_souscription')}")
                print(f"   - Statut: {sub.get('statut')}")
                print(f"   - User ID: {sub.get('user_id')}")
                print(f"   - Date création: {sub.get('created_at')}")
        elif response.status_code == 401:
            print("❌ Erreur 401: Authentification requise")
            print("💡 Vous devez fournir un token valide")
            print("\nPour obtenir un token:")
            print("   1. Connectez-vous via l'application mobile")
            print("   2. Récupérez le token depuis les logs ou le stockage sécurisé")
        elif response.status_code == 404:
            print("❌ Erreur 404: Endpoint non trouvé")
            print("💡 Le serveur backend n'a probablement pas rechargé les routes")
            print("   Solution: Redémarrer le serveur backend")
        else:
            print(f"❌ Erreur {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Détails: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Réponse: {response.text[:200]}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au serveur")
        print(f"💡 Vérifiez que le serveur backend est démarré sur {base_url}")
    except requests.exceptions.Timeout:
        print("❌ Timeout - le serveur ne répond pas")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Teste l'endpoint des souscriptions")
    parser.add_argument("--url", default="http://192.168.1.183:8000", help="URL de base du serveur")
    parser.add_argument("--token", help="Token d'authentification Bearer")
    args = parser.parse_args()
    
    test_subscriptions_endpoint(args.url, args.token)
