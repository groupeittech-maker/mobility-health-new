"""
Script pour tester le flux complet de connexion
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from datetime import timedelta

def test_full_login_flow():
    """Tester le flux complet de connexion comme dans l'API"""
    db: Session = SessionLocal()
    
    try:
        print("=" * 60)
        print("TEST DU FLUX COMPLET DE CONNEXION")
        print("=" * 60)
        
        # Simuler une requête de connexion
        username = "admin"
        password = "admin123"
        
        print(f"\n📥 Tentative de connexion:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        
        # Étape 1: Rechercher l'utilisateur
        print(f"\n1️⃣  Recherche de l'utilisateur...")
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"   ❌ Utilisateur '{username}' non trouvé")
            return False
        
        print(f"   ✅ Utilisateur trouvé: {user.username} (ID: {user.id})")
        
        # Étape 2: Vérifier le mot de passe
        print(f"\n2️⃣  Vérification du mot de passe...")
        if not verify_password(password, user.hashed_password):
            print(f"   ❌ Mot de passe incorrect")
            return False
        
        print(f"   ✅ Mot de passe correct")
        
        # Étape 3: Vérifier si l'utilisateur est actif
        print(f"\n3️⃣  Vérification du statut...")
        if not user.is_active:
            print(f"   ❌ Utilisateur inactif")
            return False
        
        print(f"   ✅ Utilisateur actif")
        
        # Étape 4: Créer les tokens
        print(f"\n4️⃣  Création des tokens...")
        try:
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.username, "role": user.role.value},
                expires_delta=access_token_expires
            )
            print(f"   ✅ Access token créé: {access_token[:50]}...")
            
            # Test de décodage du token
            from app.core.security import decode_token
            decoded = decode_token(access_token)
            if decoded:
                print(f"   ✅ Token décodé avec succès:")
                print(f"      sub: {decoded.get('sub')}")
                print(f"      role: {decoded.get('role')}")
            else:
                print(f"   ❌ Impossible de décoder le token")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors de la création du token: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Étape 5: Test Redis (optionnel)
        print(f"\n5️⃣  Test Redis (optionnel)...")
        try:
            from app.core.redis_client import get_redis
            redis = get_redis()
            if redis:
                print(f"   ✅ Redis disponible")
            else:
                print(f"   ⚠️  Redis non disponible (mais ce n'est pas bloquant)")
        except Exception as e:
            print(f"   ⚠️  Redis non disponible: {e} (mais ce n'est pas bloquant)")
        
        print(f"\n✅ Tous les tests sont passés !")
        print(f"\n💡 Le problème ne vient probablement pas de la base de données.")
        print(f"   Vérifiez que le serveur API est démarré:")
        print(f"   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    test_full_login_flow()

