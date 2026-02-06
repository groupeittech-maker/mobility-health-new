"""
Script pour vérifier tous les utilisateurs dans la base de données
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import inspect
from app.core.database import SessionLocal, engine
from app.models.user import User
from app.core.security import verify_password

def check_database_structure():
    """Vérifier la structure de la table users"""
    print("=" * 60)
    print("VÉRIFICATION DE LA STRUCTURE DE LA BASE DE DONNÉES")
    print("=" * 60)
    
    inspector = inspect(engine)
    
    # Vérifier si la table users existe
    tables = inspector.get_table_names()
    print(f"\n📊 Tables dans la base de données: {len(tables)}")
    for table in sorted(tables):
        print(f"   - {table}")
    
    if 'users' not in tables:
        print("\n❌ La table 'users' n'existe pas !")
        print("   Exécutez: alembic upgrade head")
        return False
    
    # Vérifier les colonnes de la table users
    print(f"\n📋 Colonnes de la table 'users':")
    columns = inspector.get_columns('users')
    for col in columns:
        print(f"   - {col['name']}: {col['type']} (nullable={col['nullable']})")
    
    # Vérifier les index
    indexes = inspector.get_indexes('users')
    print(f"\n🔍 Index sur la table 'users': {len(indexes)}")
    for idx in indexes:
        print(f"   - {idx['name']}: {idx['column_names']}")
    
    return True

def check_all_users():
    """Vérifier tous les utilisateurs"""
    db: Session = SessionLocal()
    
    try:
        print("\n" + "=" * 60)
        print("VÉRIFICATION DES UTILISATEURS")
        print("=" * 60)
        
        users = db.query(User).all()
        
        if not users:
            print("\n❌ Aucun utilisateur trouvé dans la base de données !")
            print("   Exécutez: python scripts/create_test_users.py")
            return False
        
        print(f"\n✅ {len(users)} utilisateur(s) trouvé(s):\n")
        
        for user in users:
            print(f"👤 {user.username} (ID: {user.id})")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role.value}")
            print(f"   Is Active: {user.is_active}")
            print(f"   Is Superuser: {user.is_superuser}")
            
            # Tester les mots de passe courants
            test_passwords = {
                'admin': 'admin123',
                'doctor': 'doctor123',
                'user': 'user123',
                'hospital_admin': 'hospital123',
                'finance': 'finance123',
            }
            
            if user.username in test_passwords:
                test_pwd = test_passwords[user.username]
                if verify_password(test_pwd, user.hashed_password):
                    print(f"   ✓ Mot de passe '{test_pwd}' correct")
                else:
                    print(f"   ❌ Mot de passe '{test_pwd}' incorrect")
            print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la vérification: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("\n🔍 Vérification complète de la base de données\n")
    
    # Vérifier la structure
    structure_ok = check_database_structure()
    
    if structure_ok:
        # Vérifier les utilisateurs
        users_ok = check_all_users()
        
        if not users_ok:
            print("\n💡 Solution:")
            print("   Exécutez: python scripts/create_test_users.py")
    else:
        print("\n💡 Solution:")
        print("   Exécutez: alembic upgrade head")

