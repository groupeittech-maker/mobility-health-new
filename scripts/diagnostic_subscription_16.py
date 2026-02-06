#!/usr/bin/env python3
"""
Script de diagnostic pour la souscription #16
Vérifie l'état de la souscription, des paiements et des attestations
"""

import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.souscription import Souscription
from app.models.paiement import Paiement
from app.models.attestation import Attestation
from app.core.enums import StatutSouscription, StatutPaiement

def diagnostic_subscription(subscription_id: int):
    """Diagnostic complet d'une souscription"""
    db = SessionLocal()
    
    try:
        print(f"\n{'='*60}")
        print(f"🔍 DIAGNOSTIC SOUSCRIPTION #{subscription_id}")
        print(f"{'='*60}\n")
        
        # 1. Vérifier la souscription
        souscription = db.query(Souscription).filter(
            Souscription.id == subscription_id
        ).first()
        
        if not souscription:
            print(f"❌ Souscription #{subscription_id} non trouvée")
            return
        
        print(f"✅ Souscription trouvée:")
        print(f"   - ID: {souscription.id}")
        print(f"   - Numéro: {souscription.numero_souscription}")
        print(f"   - Statut: {souscription.statut}")
        print(f"   - User ID: {souscription.user_id}")
        print(f"   - Créée le: {souscription.created_at}")
        print()
        
        # 2. Vérifier les paiements
        paiements = db.query(Paiement).filter(
            Paiement.souscription_id == subscription_id
        ).order_by(Paiement.created_at.desc()).all()
        
        print(f"📊 Paiements trouvés: {len(paiements)}")
        if len(paiements) == 0:
            print("   ⚠️ Aucun paiement pour cette souscription")
        else:
            for p in paiements:
                print(f"   - Paiement ID {p.id}:")
                print(f"     * Statut: {p.statut}")
                print(f"     * Montant: {p.montant}")
                print(f"     * Type: {p.type_paiement}")
                print(f"     * Date paiement: {p.date_paiement}")
                print(f"     * Créé le: {p.created_at}")
                print(f"     * Référence: {p.reference_transaction}")
        
        paiements_valides = [p for p in paiements if p.statut == StatutPaiement.VALIDE]
        print(f"\n   💰 Paiements VALIDES: {len(paiements_valides)}")
        if len(paiements_valides) == 0 and len(paiements) > 0:
            print("   ⚠️ Aucun paiement valide - c'est probablement pourquoi aucune attestation n'est créée")
        print()
        
        # 3. Vérifier les attestations
        attestations = db.query(Attestation).filter(
            Attestation.souscription_id == subscription_id
        ).order_by(Attestation.created_at.desc()).all()
        
        print(f"📄 Attestations trouvées: {len(attestations)}")
        if len(attestations) == 0:
            print("   ⚠️ Aucune attestation pour cette souscription")
        else:
            for att in attestations:
                print(f"   - Attestation ID {att.id}:")
                print(f"     * Type: {att.type_attestation}")
                print(f"     * Numéro: {att.numero_attestation}")
                print(f"     * Valide: {att.est_valide}")
                print(f"     * Chemin MinIO: {att.chemin_fichier_minio}")
                print(f"     * Bucket: {att.bucket_minio}")
                print(f"     * Paiement ID: {att.paiement_id}")
                print(f"     * Créée le: {att.created_at}")
        
        attestations_valides = [a for a in attestations if a.est_valide]
        print(f"\n   ✅ Attestations VALIDES: {len(attestations_valides)}")
        print()
        
        # 4. Analyse et recommandations
        print(f"{'='*60}")
        print("📋 ANALYSE")
        print(f"{'='*60}\n")
        
        if souscription.statut in [StatutSouscription.EN_ATTENTE, "en_attente", "pending"]:
            print("✅ Souscription en statut 'en_attente'")
            
            if len(paiements_valides) == 0:
                print("❌ Problème: Aucun paiement VALIDE trouvé")
                print("   💡 Solution: L'attestation provisoire sera créée lors du checkout/paiement")
                if len(paiements) > 0:
                    print(f"   ⚠️ Il y a {len(paiements)} paiement(s) mais aucun n'est en statut VALIDE")
                    print("   💡 Vérifiez pourquoi les paiements ne sont pas validés")
            else:
                print(f"✅ Paiement VALIDE trouvé (ID: {paiements_valides[0].id})")
                
                if len(attestations_valides) == 0:
                    print("❌ Problème: Aucune attestation provisoire malgré un paiement valide")
                    print("   💡 Solution: L'attestation devrait être créée automatiquement")
                    print("   💡 Vérifiez les logs du serveur pour voir pourquoi la création a échoué")
                else:
                    print(f"✅ Attestation(s) trouvée(s): {len(attestations_valides)}")
        else:
            print(f"ℹ️ Souscription en statut '{souscription.statut}' (pas 'en_attente')")
        
        print()
        print(f"{'='*60}")
        print("🎯 RECOMMANDATIONS")
        print(f"{'='*60}\n")
        
        if len(attestations_valides) == 0:
            if len(paiements_valides) > 0:
                print("1. Il y a un paiement valide mais pas d'attestation")
                print("   → Vérifiez les logs du serveur lors de l'appel API")
                print("   → L'attestation devrait être créée automatiquement")
                print("   → Vérifiez les erreurs MinIO ou de génération PDF")
            else:
                print("1. Aucun paiement valide trouvé")
                print("   → C'est normal qu'il n'y ait pas d'attestation")
                print("   → L'attestation sera créée lors du checkout/paiement")
        
        print("\n✅ Diagnostic terminé\n")
        
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic: {e}")
        import traceback
        traceback.print_exc()
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
    
    diagnostic_subscription(subscription_id)

