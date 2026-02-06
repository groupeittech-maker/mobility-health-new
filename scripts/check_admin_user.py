"""
Script pour vérifier l'état du compte admin
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import verify_password

def check_admin_user():
    """Vérifier l'état du compte admin"""
    db: Session = SessionLocal()
    
    try:
        admin = db.query(User).filter(User.username == 'admin').first()
        
        if not admin:
            print("❌ Le compte admin n'existe pas dans la base de données")
            return False
        
        print(f"✓ Compte admin trouvé:")
        print(f"  - ID: {admin.id}")
        print(f"  - Username: {admin.username}")
        print(f"  - Email: {admin.email}")
        print(f"  - Role: {admin.role.value}")
        print(f"  - Is Active: {admin.is_active}")
        print(f"  - Is Superuser: {admin.is_superuser}")
        
        # Tester le mot de passe
        test_password = 'admin123'
        if verify_password(test_password, admin.hashed_password):
            print(f"✓ Le mot de passe 'admin123' est correct")
        else:
            print(f"❌ Le mot de passe 'admin123' est incorrect")
            print(f"  Hash actuel: {admin.hashed_password[:30]}...")
        
        if not admin.is_active:
            print("⚠️  ATTENTION: Le compte admin est INACTIF !")
            print("   C'est probablement la cause du problème de connexion.")
            return False
        
        print("\n✅ Le compte admin semble correctement configuré")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    check_admin_user()

