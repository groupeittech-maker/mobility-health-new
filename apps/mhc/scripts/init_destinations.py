"""
Script d'initialisation / synchronisation des pays et villes de destination.

Source:
- Tous les pays via REST Countries
- Principales villes par pays via CountriesNow

Après synchronisation des pays, configurez les zones tarifaires (codes canoniques) et les
liaisons pays dans l’admin « Tarification », puis exécutez :
  python scripts/check_tarification_destinations.py --strict
pour vérifier l’alignement avec la grille voyage (INTRA_AFRIQUE, RSA_MAGHREB, etc.).
"""
import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.destination import DestinationCountry
from app.services.destination_reference import sync_destination_reference_to_db


def init_destinations():
    """Initialise les pays et villes de destination depuis les sources de référence."""
    db: Session = SessionLocal()
    
    try:
        print("🚀 Synchronisation mondiale des destinations...")
        
        # Vérifier si des pays existent déjà
        existing_count = db.query(DestinationCountry).count()
        if existing_count > 0:
            print(f"⚠️  {existing_count} pays existent déjà dans la base de données.")
            response = input("Voulez-vous continuer et mettre à jour les destinations ? (o/n): ")
            if response.lower() != 'o':
                print("❌ Opération annulée.")
                return

        stats = sync_destination_reference_to_db(
            db,
            force_refresh=True,
            max_cities_per_country=40,
        )

        print("\n✅ Synchronisation terminée !")
        print(f"   - {stats['countries_created']} nouveau(x) pays créé(s)")
        print(f"   - {stats['countries_updated']} pays mis à jour")
        print(f"   - {stats['cities_created']} nouvelle(s) ville(s) créée(s)")
        print(f"   - {stats['cities_updated']} ville(s) mise(s) à jour")
        print(f"   - {stats['countries_total']} pays de référence traités")
        print(
            "\nÉtape suivante : rattacher chaque pays utile aux zones tarifaires "
            "(codes INTRA_AFRIQUE, RSA_MAGHREB, EXTRA_AFRIQUE, INTER_AFRIQUE) "
            "puis lancer : python scripts/check_tarification_destinations.py"
        )

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la synchronisation: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_destinations()

