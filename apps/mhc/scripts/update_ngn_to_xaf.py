#!/usr/bin/env python3
"""
Script pour remplacer toutes les occurrences de NGN par XAF dans la base de données
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import SessionLocal


def update_ngn_to_xaf():
    """Remplace toutes les occurrences de NGN par XAF dans la base de données"""
    db = SessionLocal()
    
    try:
        print("🔄 Recherche et remplacement de NGN par XAF dans la base de données...")
        print("=" * 60)
        
        # Liste des tables et colonnes qui pourraient contenir des devises
        updates = [
            {
                "table": "produits_assurance",
                "column": "currency",
                "description": "Produits d'assurance"
            },
            {
                "table": "finance_accounts",
                "column": "currency",
                "description": "Comptes financiers"
            },
            {
                "table": "finance_movements",
                "column": "currency",
                "description": "Mouvements financiers"
            },
        ]
        
        total_updated = 0
        
        for update_info in updates:
            table = update_info["table"]
            column = update_info["column"]
            description = update_info["description"]
            
            # Vérifier d'abord combien d'enregistrements contiennent NGN
            check_query = text(f"""
                SELECT COUNT(*) as count 
                FROM {table} 
                WHERE {column} = 'NGN'
            """)
            
            result = db.execute(check_query)
            count = result.scalar()
            
            if count > 0:
                print(f"📊 {description}: {count} enregistrement(s) avec NGN trouvé(s)")
                
                # Mettre à jour
                update_query = text(f"""
                    UPDATE {table} 
                    SET {column} = 'XAF' 
                    WHERE {column} = 'NGN'
                """)
                
                db.execute(update_query)
                db.commit()
                
                print(f"✅ {count} enregistrement(s) mis à jour dans {table}")
                total_updated += count
            else:
                print(f"✓ {description}: Aucun enregistrement avec NGN")
        
        print("=" * 60)
        print(f"✅ Total: {total_updated} enregistrement(s) mis à jour")
        
        # Vérification finale
        print("\n🔍 Vérification finale...")
        for update_info in updates:
            table = update_info["table"]
            column = update_info["column"]
            
            check_query = text(f"""
                SELECT COUNT(*) as count 
                FROM {table} 
                WHERE {column} = 'NGN'
            """)
            
            result = db.execute(check_query)
            count = result.scalar()
            
            if count > 0:
                print(f"⚠️  ATTENTION: {count} enregistrement(s) avec NGN encore présent(s) dans {table}")
            else:
                print(f"✓ {table}: Aucun NGN restant")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la mise à jour: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Mise à jour de NGN vers XAF dans la base de données...")
    print("=" * 60)
    update_ngn_to_xaf()
    print("\n✅ Script terminé avec succès!")
    print("\n💡 Note: Si vous voyez encore NGN dans l'interface:")
    print("   1. Videz le cache du navigateur (Ctrl+Shift+Delete)")
    print("   2. Videz le localStorage: Ouvrez la console et tapez:")
    print("      localStorage.removeItem('mh_currency_pref_v1')")
    print("   3. Rechargez la page (Ctrl+F5)")
