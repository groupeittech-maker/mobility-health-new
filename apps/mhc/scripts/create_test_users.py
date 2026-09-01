"""
Script pour créer des utilisateurs de test avec différents rôles
Usage: python scripts/create_test_users.py
"""
import sys
import os
from datetime import datetime, timezone

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import engine, Base
from app.core.config import settings
from app.core.enums import Role


def create_test_users():
    """Créer des utilisateurs de test avec différents rôles"""
    from app.core.security import get_password_hash
    from app.models.user import User
    
    # Créer une session de base de données
    db = Session(engine)
    
    # Liste des utilisateurs à créer
    test_users = [
        {
            "email": "admin@mobilityhealth.com",
            "username": "admin",
            "password": "admin123",
            "full_name": "Administrateur Principal",
            "role": "admin",
            "is_active": True,
            "is_superuser": True
        },
        {
            "email": "doctor@mobilityhealth.com",
            "username": "doctor",
            "password": "doctor123",
            "full_name": "Dr. Jean Dupont",
            "role": "doctor",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "medical.reviewer@mobilityhealth.com",
            "username": "mh_medical",
            "password": "medic123",
            "full_name": "Médecin Mobility Health",
            "role": "medical_reviewer",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "hospital@mobilityhealth.com",
            "username": "hospital_admin",
            "password": "hospital123",
            "full_name": "Admin Hôpital",
            "role": "hospital_admin",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "finance@mobilityhealth.com",
            "username": "finance",
            "password": "finance123",
            "full_name": "Gestionnaire Financier",
            "role": "finance_manager",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "technique@mobilityhealth.com",
            "username": "mh_technique",
            "password": "tech123",
            "full_name": "Agent Technique MH",
            "role": "technical_reviewer",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "production@mobilityhealth.com",
            "username": "mh_production",
            "password": "prod123",
            "full_name": "Agent Production MH",
            "role": "production_agent",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "sos@mobilityhealth.com",
            "username": "sos_operator",
            "password": "sos123",
            "full_name": "Opérateur SOS",
            "role": "sos_operator",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "comptable.mh@mobilityhealth.com",
            "username": "comptable_mh",
            "password": "comptaMH123",
            "full_name": "Agent Comptable MH",
            "role": "agent_comptable_mh",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "comptable.assureur@mobilityhealth.com",
            "username": "comptable_assureur",
            "password": "comptaAss123",
            "full_name": "Agent Comptable Assureur",
            "role": "agent_comptable_assureur",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "comptable.hopital@mobilityhealth.com",
            "username": "comptable_hopital",
            "password": "comptaHop123",
            "full_name": "Agent Comptable Hôpital",
            "role": "agent_comptable_hopital",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "sinistre.mh@mobilityhealth.com",
            "username": "sinistre_mh",
            "password": "sinistreMH123",
            "full_name": "Agent Sinistre MH",
            "role": "agent_sinistre_mh",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "sinistre.assureur@mobilityhealth.com",
            "username": "sinistre_assureur",
            "password": "sinistreAss123",
            "full_name": "Agent Sinistre Assureur",
            "role": "agent_sinistre_assureur",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "reception.hopital@mobilityhealth.com",
            "username": "reception_hopital",
            "password": "reception123",
            "full_name": "Agent Réception Hôpital",
            "role": "agent_reception_hopital",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "medecin.referent@mobilityhealth.com",
            "username": "medecin_referent",
            "password": "mederef123",
            "full_name": "Médecin Référent MH",
            "role": "medecin_referent_mh",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "medecin.hopital@mobilityhealth.com",
            "username": "medecin_hopital",
            "password": "medhop123",
            "full_name": "Médecin Hôpital",
            "role": "medecin_hopital",
            "is_active": True,
            "is_superuser": False
        },
        {
            "email": "user@mobilityhealth.com",
            "username": "user",
            "password": "user123",
            "full_name": "Utilisateur Test",
            "role": "user",
            "is_active": True,
            "is_superuser": False
        },
    ]
    
    created_users = []
    existing_users = []
    now = datetime.now(timezone.utc)
    
    try:
        for user_data in test_users:
            # Vérifier si l'utilisateur existe déjà
            existing_user = db.query(User).filter(
                (User.email == user_data["email"]) | (User.username == user_data["username"])
            ).first()
            
            if existing_user:
                existing_users.append(user_data["username"])
                print(f"⚠️  Utilisateur '{user_data['username']}' existe déjà")
                continue
            
            # Convertir le rôle string en enum
            role_value = user_data["role"]
            try:
                role_enum = Role(role_value)
            except ValueError:
                role_enum = Role.__members__.get(role_value.upper(), Role.USER)
            # Créer l'utilisateur
            hashed_password = get_password_hash(user_data["password"])
            
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                hashed_password=hashed_password,
                full_name=user_data["full_name"],
                role=role_enum,
                is_active=user_data["is_active"],
                is_superuser=user_data["is_superuser"],
                created_at=now,
                updated_at=now
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            created_users.append(user_data["username"])
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la création des utilisateurs: {e}")
        raise
    finally:
        db.close()
        
    print("\n" + "="*60)
    print("CRÉATION DES UTILISATEURS DE TEST")
    print("="*60)
    
    if created_users:
        print(f"\n✅ {len(created_users)} utilisateur(s) créé(s):")
        for username in created_users:
            user_data = next(u for u in test_users if u["username"] == username)
            print(f"   - {username} ({user_data['role']})")
    
    if existing_users:
        print(f"\n⚠️  {len(existing_users)} utilisateur(s) existant(s) déjà:")
        for username in existing_users:
            print(f"   - {username}")
    
    print("\n" + "="*60)
    print("IDENTIFIANTS DE CONNEXION")
    print("="*60)
    print("\n📋 Liste complète des comptes:\n")
    
    for user_data in test_users:
        print(f"Rôle: {user_data['role'].upper()}")
        print(f"  Username: {user_data['username']}")
        print(f"  Password: {user_data['password']}")
        print(f"  Email: {user_data['email']}")
        print()
    
    print("="*60)
    print("\n💡 Vous pouvez maintenant vous connecter au back office avec ces identifiants.")
    print("   URL: http://localhost:3000/login.html\n")


if __name__ == "__main__":
    create_test_users()

