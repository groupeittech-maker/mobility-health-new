"""
Script pour vérifier le type réel de la colonne role dans la base de données
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.core.database import engine

def check_role_column_type():
    """Vérifier le type réel de la colonne role"""
    print("=" * 60)
    print("VÉRIFICATION DU TYPE DE LA COLONNE ROLE")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Vérifier si le type ENUM 'role' existe
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 
                FROM pg_type 
                WHERE typname = 'role'
            ) as enum_exists;
        """))
        enum_exists = result.fetchone()[0]
        
        print(f"\n📊 Type ENUM 'role' existe: {enum_exists}")
        
        if enum_exists:
            # Récupérer les valeurs de l'ENUM
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                WHERE pg_type.typname = 'role'
                ORDER BY enumsortorder;
            """))
            enum_values = [row[0] for row in result.fetchall()]
            print(f"   Valeurs de l'ENUM: {enum_values}")
        
        # Vérifier le type de la colonne role dans la table users
        result = conn.execute(text("""
            SELECT 
                data_type,
                udt_name,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'users' 
            AND column_name = 'role';
        """))
        
        row = result.fetchone()
        if row:
            data_type, udt_name, max_length = row
            print(f"\n📋 Type de la colonne 'role' dans 'users':")
            print(f"   data_type: {data_type}")
            print(f"   udt_name: {udt_name}")
            print(f"   max_length: {max_length}")
            
            if data_type == 'USER-DEFINED' and udt_name == 'role':
                print("\n✅ La colonne utilise bien le type ENUM 'role'")
            elif data_type == 'character varying' or data_type == 'varchar':
                print("\n⚠️  La colonne est de type VARCHAR, pas ENUM !")
                print("   Cela peut causer des problèmes de comparaison.")
                return False
            else:
                print(f"\n⚠️  Type inattendu: {data_type}")
                return False
        
        # Tester une requête avec un utilisateur
        result = conn.execute(text("""
            SELECT username, role, role::text as role_text
            FROM users 
            WHERE username = 'admin'
            LIMIT 1;
        """))
        
        row = result.fetchone()
        if row:
            username, role, role_text = row
            print(f"\n👤 Test avec l'utilisateur 'admin':")
            print(f"   username: {username}")
            print(f"   role (type Python): {type(role).__name__}")
            print(f"   role (valeur): {role}")
            print(f"   role::text: {role_text}")
        
        return True

if __name__ == "__main__":
    try:
        check_role_column_type()
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

