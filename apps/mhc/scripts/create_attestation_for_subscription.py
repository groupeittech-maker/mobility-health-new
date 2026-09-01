#!/usr/bin/env python3
"""
Script pour créer manuellement une attestation provisoire pour une souscription
"""

import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.souscription import Souscription
from app.models.paiement import Paiement
from app.models.attestation import Attestation
from app.core.enums import StatutPaiement
from app.services.attestation_service import AttestationService

def create_attestation_for_subscription(subscription_id: int):
    """Créer une attestation provisoire pour une souscription"""
    db = SessionLocal()
    
    try:
        print(f"\n{'='*60}")
        print(f"🔧 CRÉATION D'ATTESTATION PROVISOIRE")
        print(f"{'='*60}\n")
        
        # 1. Vérifier la souscription
        souscription = db.query(Souscription).filter(
            Souscription.id == subscription_id
        ).first()
        
        if not souscription:
            print(f"❌ Souscription #{subscription_id} non trouvée")
            return False
        
        print(f"✅ Souscription trouvée: {souscription.numero_souscription}")
        
        # 2. Vérifier s'il y a déjà une attestation
        attestation_existante = db.query(Attestation).filter(
            Attestation.souscription_id == subscription_id,
            Attestation.type_attestation == "provisoire",
            Attestation.est_valide == True
        ).first()
        
        if attestation_existante:
            print(f"⚠️ Une attestation provisoire existe déjà (ID: {attestation_existante.id})")
            print(f"   Numéro: {attestation_existante.numero_attestation}")
            response = input("   Voulez-vous quand même créer une nouvelle attestation? (o/N): ")
            if response.lower() != 'o':
                print("❌ Création annulée")
                return False
        
        # 3. Chercher un paiement valide
        paiement = db.query(Paiement).filter(
            Paiement.souscription_id == subscription_id,
            Paiement.statut == StatutPaiement.VALIDE
        ).order_by(Paiement.created_at.desc()).first()
        
        if not paiement:
            print("❌ Aucun paiement VALIDE trouvé pour cette souscription")
            print("   L'attestation provisoire nécessite un paiement valide")
            return False
        
        print(f"✅ Paiement VALIDE trouvé (ID: {paiement.id}, Montant: {paiement.montant})")
        
        # 4. Récupérer l'utilisateur
        from app.models.user import User
        user = db.query(User).filter(User.id == souscription.user_id).first()
        
        if not user:
            print(f"❌ Utilisateur (ID: {souscription.user_id}) non trouvé")
            return False
        
        print(f"✅ Utilisateur trouvé: {user.email}")
        
        # 5. Créer l'attestation provisoire
        print("\n🔄 Création de l'attestation provisoire...")
        try:
            attestation = AttestationService.create_attestation_provisoire(
                db=db,
                souscription=souscription,
                paiement=paiement,
                user=user
            )
            
            print(f"\n✅ Attestation provisoire créée avec succès!")
            print(f"   - ID: {attestation.id}")
            print(f"   - Numéro: {attestation.numero_attestation}")
            print(f"   - Type: {attestation.type_attestation}")
            print(f"   - Chemin MinIO: {attestation.chemin_fichier_minio}")
            print(f"   - Bucket: {attestation.bucket_minio}")
            print(f"   - Valide: {attestation.est_valide}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Erreur lors de la création de l'attestation: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    subscription_id = 16
    if len(sys.argv) > 1:
        try:
            subscription_id = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [subscription_id]")
            sys.exit(1)
    
    success = create_attestation_for_subscription(subscription_id)
    sys.exit(0 if success else 1)

