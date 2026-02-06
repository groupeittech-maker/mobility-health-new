"""
Script de test pour vérifier que l'endpoint stats fonctionne
"""
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Test d'import du module stats...")
    from app.api.v1 import stats
    print("✅ Module stats importé avec succès")
    
    print("\nVérification des routes...")
    print(f"Router: {stats.router}")
    print(f"Routes disponibles:")
    for route in stats.router.routes:
        print(f"  - {route.methods} {route.path}")
    
    print("\n✅ Tout semble correct!")
    print("\nEndpoints disponibles:")
    print("  - POST /api/v1/stats/query")
    print("  - GET /api/v1/stats/schema")
    print("  - GET /api/v1/stats/health")
    print("  - GET /stats-dashboard.html")
    
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("\nVérifiez que:")
    print("  1. Le fichier app/api/v1/stats.py existe")
    print("  2. Toutes les dépendances sont installées")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

