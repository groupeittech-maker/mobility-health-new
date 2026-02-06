"""
Script pour vérifier si un utilisateur existe dans la base de données
"""
import sys
from app.core.database import SessionLocal
from app.models.user import User

def check_user(username: str = None, email: str = None):
    """Vérifier si un utilisateur existe"""
    db = SessionLocal()
    try:
        if username:
            user = db.query(User).filter(User.username == username).first()
            if user:
                print(f"✓ Utilisateur trouvé par username '{username}':")
                print(f"  - ID: {user.id}")
                print(f"  - Email: {user.email}")
                print(f"  - Username: {user.username}")
                print(f"  - Full name: {user.full_name}")
                print(f"  - Role: {user.role.value}")
                print(f"  - Is active: {user.is_active}")
                print(f"  - Created at: {user.created_at}")
                print(f"  - Created by ID: {user.created_by_id}")
                return True
            else:
                print(f"✗ Aucun utilisateur trouvé avec le username '{username}'")
                return False
        
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                print(f"✓ Utilisateur trouvé par email '{email}':")
                print(f"  - ID: {user.id}")
                print(f"  - Email: {user.email}")
                print(f"  - Username: {user.username}")
                print(f"  - Full name: {user.full_name}")
                print(f"  - Role: {user.role.value}")
                print(f"  - Is active: {user.is_active}")
                print(f"  - Created at: {user.created_at}")
                print(f"  - Created by ID: {user.created_by_id}")
                return True
            else:
                print(f"✗ Aucun utilisateur trouvé avec l'email '{email}'")
                return False
        
        print("Veuillez fournir un username ou un email")
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_user.py <username>")
        print("   ou: python scripts/check_user.py --email <email>")
        sys.exit(1)
    
    if sys.argv[1] == "--email" and len(sys.argv) > 2:
        check_user(email=sys.argv[2])
    else:
        check_user(username=sys.argv[1])

