"""
Script pour tester la comparaison des rôles
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.user import User
from app.core.enums import Role

def test_role_comparison():
    """Tester la comparaison des rôles"""
    db: Session = SessionLocal()
    
    try:
        print("=" * 60)
        print("TEST DE COMPARAISON DES RÔLES")
        print("=" * 60)
        
        # Récupérer l'utilisateur admin
        admin = db.query(User).filter(User.username == 'admin').first()
        
        if not admin:
            print("❌ Utilisateur admin non trouvé")
            return
        
        print(f"\n👤 Utilisateur: {admin.username}")
        print(f"   Role (attribut): {admin.role}")
        print(f"   Type: {type(admin.role)}")
        print(f"   Role.value: {admin.role.value if hasattr(admin.role, 'value') else 'N/A'}")
        
        # Tester différentes comparaisons
        print(f"\n🔍 Tests de comparaison:")
        
        # Test 1: Comparaison directe avec l'enum
        test1 = admin.role == Role.ADMIN
        print(f"   admin.role == Role.ADMIN: {test1}")
        
        # Test 2: Comparaison avec la valeur string
        test2 = admin.role.value == "admin"
        print(f"   admin.role.value == 'admin': {test2}")
        
        # Test 3: Comparaison avec la valeur en majuscule
        test3 = str(admin.role).upper() == "ADMIN"
        print(f"   str(admin.role).upper() == 'ADMIN': {test3}")
        
        # Test 4: Vérifier la valeur brute depuis la DB
        with db.connection() as conn:
            result = conn.execute(text("""
                SELECT role::text as role_text
                FROM users 
                WHERE username = 'admin'
            """))
            db_role = result.fetchone()[0]
            print(f"\n📊 Valeur brute depuis la DB: '{db_role}'")
            print(f"   Type: {type(db_role)}")
            print(f"   db_role == 'admin': {db_role == 'admin'}")
            print(f"   db_role == 'ADMIN': {db_role == 'ADMIN'}")
            print(f"   db_role.lower() == 'admin': {db_role.lower() == 'admin'}")
        
        # Test 5: Vérifier comment SQLAlchemy mappe l'ENUM
        print(f"\n🔧 Mapping SQLAlchemy:")
        print(f"   admin.role: {repr(admin.role)}")
        if isinstance(admin.role, Role):
            print(f"   C'est une instance de Role enum")
        elif isinstance(admin.role, str):
            print(f"   C'est une string: '{admin.role}'")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_role_comparison()

