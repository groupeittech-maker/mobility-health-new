"""
Script pour créer ou réinitialiser l'utilisateur 'user' avec le mot de passe 'user123'
Usage: python scripts/fix_user_login.py
"""
import sys
import os
from datetime import datetime, timezone

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.core.enums import Role


def fix_user_login():
    """Créer ou réinitialiser l'utilisateur 'user'"""
    db = SessionLocal()
    
    try:
        # Vérifier si l'utilisateur existe
        user = db.query(User).filter(User.username == "user").first()
        
        password = "user123"
        password_hash = get_password_hash(password)
        
        if user:
            print(f"✓ Utilisateur 'user' trouvé")
            print(f"  - Email: {user.email}")
            print(f"  - Rôle: {user.role.value}")
            print(f"  - Actif: {user.is_active}")
            
            # Vérifier si le mot de passe est correct
            if verify_password(password, user.hashed_password):
                print(f"✓ Le mot de passe est correct")
            else:
                print(f"⚠️  Le mot de passe ne correspond pas, mise à jour...")
                user.hashed_password = password_hash
                user.updated_at = datetime.now(timezone.utc)
                db.commit()
                print(f"✓ Mot de passe mis à jour")
            
            # S'assurer que l'utilisateur est actif
            if not user.is_active:
                print(f"⚠️  L'utilisateur est inactif, activation...")
                user.is_active = True
                user.updated_at = datetime.now(timezone.utc)
                db.commit()
                print(f"✓ Utilisateur activé")
        else:
            print(f"✗ Utilisateur 'user' non trouvé, création...")
            user = User(
                email="user@mobilityhealth.com",
                username="user",
                hashed_password=password_hash,
                full_name="Utilisateur Test",
                role=Role.USER,
                is_active=True,
                is_superuser=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✓ Utilisateur 'user' créé avec succès")
            print(f"  - Email: {user.email}")
            print(f"  - Username: {user.username}")
            print(f"  - Rôle: {user.role.value}")
            print(f"  - Mot de passe: {password}")
        
        print(f"\n✅ L'utilisateur 'user' est prêt à être utilisé")
        print(f"   Username: user")
        print(f"   Password: user123")
        
    except Exception as e:
        print(f"✗ Erreur: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Fix User Login - Création/Réinitialisation de l'utilisateur 'user'")
    print("=" * 60)
    print()
    
    success = fix_user_login()
    
    if success:
        print()
        print("=" * 60)
        print("✅ Script terminé avec succès")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("✗ Erreur lors de l'exécution du script")
        print("=" * 60)
        sys.exit(1)

