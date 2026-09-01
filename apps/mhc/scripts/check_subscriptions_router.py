#!/usr/bin/env python3
"""
Script pour vérifier si le router subscriptions peut être importé correctement
"""
import sys
import traceback

def check_subscriptions_router():
    """Vérifier l'import du router subscriptions"""
    print("=" * 60)
    print("Vérification du router subscriptions")
    print("=" * 60)
    print()
    
    # Test 1: Importer le module subscriptions
    print("1. Test d'import du module subscriptions...")
    try:
        from app.api.v1 import subscriptions
        print("   ✓ Module subscriptions importé avec succès")
    except Exception as e:
        print(f"   ✗ Erreur lors de l'import: {e}")
        print("   Traceback complet:")
        traceback.print_exc()
        return False
    
    # Test 2: Vérifier que le router existe
    print()
    print("2. Vérification du router...")
    try:
        router = subscriptions.router
        print(f"   ✓ Router trouvé: {type(router)}")
        print(f"   Nombre de routes: {len(router.routes)}")
        
        # Lister les routes
        print()
        print("   Routes disponibles:")
        for route in router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = ', '.join(route.methods) if route.methods else 'N/A'
                print(f"      {methods:8} {route.path}")
    except Exception as e:
        print(f"   ✗ Erreur lors de l'accès au router: {e}")
        traceback.print_exc()
        return False
    
    # Test 3: Vérifier l'import dans __init__.py
    print()
    print("3. Vérification de l'import dans app.api.v1.__init__...")
    try:
        from app.api.v1 import api_router
        print("   ✓ api_router importé avec succès")
        
        # Vérifier si subscriptions est dans les routers inclus
        print("   Vérification des routers inclus...")
        # Note: On ne peut pas facilement vérifier les routers inclus sans accéder aux internals
        # Mais on peut vérifier que le module peut être importé depuis __init__
        from app.api.v1.__init__ import subscriptions as subscriptions_from_init
        print("   ✓ subscriptions peut être importé depuis __init__")
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        traceback.print_exc()
        return False
    
    print()
    print("=" * 60)
    print("✅ Tous les tests sont passés!")
    print("=" * 60)
    print()
    print("💡 Si le router peut être importé mais l'endpoint retourne 404:")
    print("   1. Redémarrez le serveur backend")
    print("   2. Vérifiez les logs du serveur au démarrage")
    print("   3. Vérifiez que app/api/v1/__init__.py inclut bien le router")
    
    return True

if __name__ == "__main__":
    success = check_subscriptions_router()
    sys.exit(0 if success else 1)
