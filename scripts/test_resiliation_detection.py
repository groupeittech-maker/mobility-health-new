"""
Script de test pour vérifier la détection des résiliations dans les transactions comptables
"""
import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.souscription import Souscription
from app.models.paiement import Paiement
from app.models.finance_refund import Refund
from app.core.enums import StatutSouscription, StatutPaiement

def test_resiliation_detection():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("TEST DE DÉTECTION DES RÉSILIATIONS")
        print("=" * 60)
        
        # 1. Trouver toutes les souscriptions résiliées
        print("\n1. Souscriptions avec demande_resiliation = 'approved':")
        resiliated_subscriptions = db.query(Souscription).filter(
            Souscription.demande_resiliation == "approved"
        ).all()
        
        print(f"   Trouvé {len(resiliated_subscriptions)} souscription(s) résiliée(s)")
        for sub in resiliated_subscriptions:
            print(f"   - Souscription {sub.id}: statut={sub.statut}, demande_resiliation={sub.demande_resiliation}")
        
        # 2. Trouver les paiements associés
        print("\n2. Paiements associés aux souscriptions résiliées:")
        for sub in resiliated_subscriptions:
            payments = db.query(Paiement).filter(
                Paiement.souscription_id == sub.id
            ).all()
            print(f"   Souscription {sub.id}: {len(payments)} paiement(s)")
            for payment in payments:
                print(f"     - Paiement {payment.id}: statut={payment.statut}, montant={payment.montant}, montant_rembourse={payment.montant_rembourse}")
        
        # 3. Trouver les remboursements
        print("\n3. Remboursements pour les souscriptions résiliées:")
        for sub in resiliated_subscriptions:
            refunds = db.query(Refund).filter(
                Refund.souscription_id == sub.id,
                Refund.statut == "completed"
            ).all()
            print(f"   Souscription {sub.id}: {len(refunds)} remboursement(s)")
            for refund in refunds:
                print(f"     - Remboursement {refund.id}: montant={refund.montant}, statut={refund.statut}")
        
        # 4. Vérifier les souscriptions avec statut RESILIEE
        print("\n4. Souscriptions avec statut RESILIEE:")
        resiliated_by_status = db.query(Souscription).filter(
            Souscription.statut == StatutSouscription.RESILIEE
        ).all()
        print(f"   Trouvé {len(resiliated_by_status)} souscription(s) avec statut RESILIEE")
        for sub in resiliated_by_status:
            print(f"   - Souscription {sub.id}: statut={sub.statut}, demande_resiliation={sub.demande_resiliation}")
        
        # 5. Test de la requête de l'endpoint
        print("\n5. Test de la requête similaire à l'endpoint:")
        payments = db.query(Paiement).order_by(Paiement.created_at.desc()).limit(10).all()
        print(f"   Vérification des {len(payments)} derniers paiements:")
        for payment in payments:
            subscription = payment.souscription
            if subscription:
                is_resiliation = (
                    subscription.demande_resiliation == "approved" or
                    subscription.statut == StatutSouscription.RESILIEE
                )
                if is_resiliation:
                    print(f"     ✓ Paiement {payment.id} -> Souscription {subscription.id} est résiliée")
                    print(f"       demande_resiliation={subscription.demande_resiliation}, statut={subscription.statut}")
                else:
                    print(f"     ✗ Paiement {payment.id} -> Souscription {subscription.id} n'est pas résiliée")
                    print(f"       demande_resiliation={subscription.demande_resiliation}, statut={subscription.statut}")
        
        print("\n" + "=" * 60)
        print("TEST TERMINÉ")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_resiliation_detection()






