"""
Script d'initialisation des pays et villes de destination
Ce script peuple la base de données avec les pays actuellement pris en charge
"""
import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.destination import DestinationCountry, DestinationCity

# Liste des pays actuellement pris en charge (basée sur le code existant)
PAYS_INITIAUX = [
    {'code': 'BJ', 'nom': 'Bénin', 'ordre': 1},
    {'code': 'BF', 'nom': 'Burkina Faso', 'ordre': 2},
    {'code': 'CM', 'nom': 'Cameroun', 'ordre': 3},
    {'code': 'CG', 'nom': 'Congo', 'ordre': 4},
    {'code': 'CI', 'nom': "Côte d'Ivoire", 'ordre': 5},
    {'code': 'FR', 'nom': 'France', 'ordre': 6},
    {'code': 'GA', 'nom': 'Gabon', 'ordre': 7},
    {'code': 'GH', 'nom': 'Ghana', 'ordre': 8},
    {'code': 'GN', 'nom': 'Guinée', 'ordre': 9},
    {'code': 'IT', 'nom': 'Italie', 'ordre': 10},
    {'code': 'ML', 'nom': 'Mali', 'ordre': 11},
    {'code': 'MA', 'nom': 'Maroc', 'ordre': 12},
    {'code': 'NE', 'nom': 'Niger', 'ordre': 13},
    {'code': 'NG', 'nom': 'Nigeria', 'ordre': 14},
    {'code': 'RW', 'nom': 'Rwanda', 'ordre': 15},
    {'code': 'SN', 'nom': 'Sénégal', 'ordre': 16},
    {'code': 'TG', 'nom': 'Togo', 'ordre': 17},
    {'code': 'TN', 'nom': 'Tunisie', 'ordre': 18},
]

# Villes principales par pays (exemples)
VILLES_PAR_PAYS = {
    "Côte d'Ivoire": ['Abidjan', 'Yamoussoukro', 'Bouaké', 'San-Pédro'],
    'France': ['Paris', 'Lyon', 'Marseille', 'Toulouse'],
    'Sénégal': ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor'],
    'Cameroun': ['Douala', 'Yaoundé', 'Garoua', 'Bafoussam'],
    'Maroc': ['Casablanca', 'Rabat', 'Marrakech', 'Fès'],
    'Tunisie': ['Tunis', 'Sfax', 'Sousse', 'Kairouan'],
    'Bénin': ['Cotonou', 'Porto-Novo', 'Parakou', 'Abomey'],
    'Burkina Faso': ['Ouagadougou', 'Bobo-Dioulasso', 'Koudougou'],
    'Ghana': ['Accra', 'Kumasi', 'Tamale', 'Sekondi-Takoradi'],
    'Mali': ['Bamako', 'Sikasso', 'Mopti', 'Kayes'],
    'Niger': ['Niamey', 'Zinder', 'Maradi'],
    'Nigeria': ['Lagos', 'Abuja', 'Kano', 'Ibadan'],
    'Rwanda': ['Kigali', 'Butare', 'Gitarama'],
    'Togo': ['Lomé', 'Sokodé', 'Kara'],
    'Gabon': ['Libreville', 'Port-Gentil', 'Franceville'],
    'Guinée': ['Conakry', 'Nzérékoré', 'Kankan'],
    'Congo': ['Brazzaville', 'Pointe-Noire'],
    'Italie': ['Rome', 'Milan', 'Naples', 'Turin'],
}


def init_destinations():
    """Initialise les pays et villes de destination"""
    db: Session = SessionLocal()
    
    try:
        print("🚀 Initialisation des pays et villes de destination...")
        
        # Vérifier si des pays existent déjà
        existing_count = db.query(DestinationCountry).count()
        if existing_count > 0:
            print(f"⚠️  {existing_count} pays existent déjà dans la base de données.")
            response = input("Voulez-vous continuer et ajouter les pays manquants ? (o/n): ")
            if response.lower() != 'o':
                print("❌ Opération annulée.")
                return
        
        pays_crees = 0
        villes_creees = 0
        
        for pays_data in PAYS_INITIAUX:
            # Vérifier si le pays existe déjà
            existing = db.query(DestinationCountry).filter(
                DestinationCountry.code == pays_data['code']
            ).first()
            
            if existing:
                print(f"✓ Pays '{pays_data['nom']}' existe déjà (code: {pays_data['code']})")
                pays = existing
            else:
                # Créer le pays
                pays = DestinationCountry(
                    code=pays_data['code'],
                    nom=pays_data['nom'],
                    est_actif=True,
                    ordre_affichage=pays_data['ordre']
                )
                db.add(pays)
                db.flush()  # Pour obtenir l'ID
                print(f"✓ Pays '{pays_data['nom']}' créé (code: {pays_data['code']})")
                pays_crees += 1
            
            # Ajouter les villes pour ce pays
            villes = VILLES_PAR_PAYS.get(pays_data['nom'], [])
            for idx, ville_nom in enumerate(villes, start=1):
                # Vérifier si la ville existe déjà
                existing_city = db.query(DestinationCity).filter(
                    DestinationCity.pays_id == pays.id,
                    DestinationCity.nom == ville_nom
                ).first()
                
                if not existing_city:
                    ville = DestinationCity(
                        pays_id=pays.id,
                        nom=ville_nom,
                        est_actif=True,
                        ordre_affichage=idx
                    )
                    db.add(ville)
                    villes_creees += 1
                    print(f"  └─ Ville '{ville_nom}' ajoutée")
        
        # Commit toutes les modifications
        db.commit()
        
        print(f"\n✅ Initialisation terminée !")
        print(f"   - {pays_crees} nouveau(x) pays créé(s)")
        print(f"   - {villes_creees} nouvelle(s) ville(s) créée(s)")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de l'initialisation: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_destinations()

