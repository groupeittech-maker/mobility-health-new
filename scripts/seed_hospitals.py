"""
Script utilitaire pour créer ou mettre à jour des hôpitaux avec coordonnées GPS.

Usage :
    python scripts/seed_hospitals.py

Vous pouvez adapter la liste HOSPITALS_SEED_DATA selon vos besoins.
"""

from decimal import Decimal
from typing import List, Dict

from app.core.database import SessionLocal
from app.models.hospital import Hospital


HOSPITALS_SEED_DATA: List[Dict] = [
    {
        "nom": "Centre Hospitalier Universitaire de Cocody",
        "ville": "Abidjan",
        "pays": "Côte d'Ivoire",
        "adresse": "Boulevard François Mitterrand, Cocody",
        "telephone": "+225-27-22-44-50-01",
        "email": "contact@chu-cocody.ci",
        "latitude": Decimal("5.350250"),
        "longitude": Decimal("-3.989430"),
        "specialites": "Urgences, Médecine interne, Chirurgie",
    },
    {
        "nom": "Hôpital Général de Yopougon",
        "ville": "Abidjan",
        "pays": "Côte d'Ivoire",
        "adresse": "Quartier Wassakara, Yopougon",
        "telephone": "+225-27-23-32-15-20",
        "email": "info@hopital-yopougon.ci",
        "latitude": Decimal("5.375800"),
        "longitude": Decimal("-4.054890"),
        "specialites": "Urgences, Pédiatrie",
    },
    {
        "nom": "Polyclinique Internationale Sainte Anne-Marie (PISAM)",
        "ville": "Abidjan",
        "pays": "Côte d'Ivoire",
        "adresse": "Rue Thomas Edison, Zone 4C",
        "telephone": "+225-27-21-35-14-14",
        "email": "urgence@pisam.ci",
        "latitude": Decimal("5.305870"),
        "longitude": Decimal("-3.999100"),
        "specialites": "Urgences, Cardiologie, Oncologie",
    },
    {
        "nom": "Hôpital Général de Grand-Bassam",
        "ville": "Grand-Bassam",
        "pays": "Côte d'Ivoire",
        "adresse": "Rue du Wharf",
        "telephone": "+225-27-21-30-12-14",
        "email": "contact@hg-grandbassam.ci",
        "latitude": Decimal("5.207890"),
        "longitude": Decimal("-3.739720"),
        "specialites": "Urgences, Médecine générale",
    },
    {
        "nom": "Hôpital Mère-Enfant Dominique Ouattara",
        "ville": "Bingerville",
        "pays": "Côte d'Ivoire",
        "adresse": "Route de Bingerville",
        "telephone": "+225-27-22-44-66-00",
        "email": "info@hme.ci",
        "latitude": Decimal("5.355430"),
        "longitude": Decimal("-3.874320"),
        "specialites": "Pédiatrie, Maternité",
    },
    {
        "nom": "Centre Hospitalier Régional de Bouaké",
        "ville": "Bouaké",
        "pays": "Côte d'Ivoire",
        "adresse": "Quartier Air France 1",
        "telephone": "+225-27-31-63-20-20",
        "email": "contact@chr-bouake.ci",
        "latitude": Decimal("7.693850"),
        "longitude": Decimal("-5.030310"),
        "specialites": "Urgences, Traumatologie",
    },
]


def seed_hospitals():
    db = SessionLocal()
    try:
        for entry in HOSPITALS_SEED_DATA:
            hospital = (
                db.query(Hospital)
                .filter(
                    Hospital.nom == entry["nom"],
                    Hospital.ville == entry["ville"],
                )
                .first()
            )
            
            if hospital:
                for key, value in entry.items():
                    setattr(hospital, key, value)
                hospital.est_actif = True
                action = "Mis à jour"
            else:
                hospital = Hospital(**entry)
                db.add(hospital)
                action = "Ajouté"
            
            print(f"{action} : {hospital.nom} ({hospital.ville})")
        
        db.commit()
        print("✅ Synchronisation des hôpitaux terminée.")
    except Exception as exc:
        db.rollback()
        print("❌ Échec lors de l'enregistrement des hôpitaux:", exc)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_hospitals()

















