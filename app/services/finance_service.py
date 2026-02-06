"""
Service pour la gestion financière avec transactions ACID et anti-doublon
"""
from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import uuid

from app.models.finance_account import Account
from app.models.finance_movement import Movement
from app.models.finance_repartition import Repartition
from app.models.finance_refund import Refund
from app.models.paiement import Paiement
from app.models.souscription import Souscription
from app.models.produit_assurance import ProduitAssurance
from app.core.enums import CleRepartition, StatutPaiement

logger = logging.getLogger(__name__)


class FinanceService:
    """Service pour les opérations financières"""
    
    @staticmethod
    def check_duplicate_reference(db: Session, reference: str) -> bool:
        """Vérifier si une référence existe déjà (anti-doublon)"""
        existing = db.query(Movement).filter(Movement.reference == reference).first()
        return existing is not None
    
    @staticmethod
    def create_movement(
        db: Session,
        account_id: int,
        movement_type: str,
        amount: Decimal,
        description: str,
        reference: Optional[str] = None,
        reference_type: Optional[str] = None,
        related_id: Optional[int] = None,
        currency: str = "EUR"
    ) -> Movement:
        """Créer un mouvement financier avec anti-doublon"""
        # Générer une référence unique si non fournie
        if not reference:
            reference = f"MOV-{uuid.uuid4().hex[:16].upper()}"
        
        # Vérifier anti-doublon
        if FinanceService.check_duplicate_reference(db, reference):
            raise ValueError(f"Duplicate reference: {reference}")
        
        # Créer le mouvement
        movement = Movement(
            account_id=account_id,
            movement_type=movement_type,
            amount=amount,
            currency=currency,
            description=description,
            reference=reference,
            reference_type=reference_type,
            related_id=related_id
        )
        
        db.add(movement)
        
        # Mettre à jour le solde du compte
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        if movement_type in ["credit", "payment", "refund"]:
            account.balance += amount
        elif movement_type in ["debit", "repartition"]:
            account.balance -= amount
        
        return movement
    
    @staticmethod
    def calculate_repartition(
        db: Session,
        souscription_id: int,
        paiement_id: int,
        cle_repartition: CleRepartition,
        montant_total: Decimal
    ) -> Dict[str, Decimal]:
        """Calculer la répartition selon la clé de répartition"""
        souscription = db.query(Souscription).filter(Souscription.id == souscription_id).first()
        if not souscription:
            raise ValueError(f"Subscription {souscription_id} not found")
        
        repartition = {}
        
        if cle_repartition == CleRepartition.FIXE:
            # Répartition fixe : tout dans un compte
            repartition["default"] = montant_total
        
        elif cle_repartition == CleRepartition.PAR_PERSONNE:
            # Répartition par personne : diviser par le nombre de personnes
            projet = souscription.projet_voyage
            if projet:
                nb_personnes = getattr(projet, 'nb_personnes', 1) or 1
                montant_par_personne = montant_total / nb_personnes
                repartition["par_personne"] = montant_par_personne
                repartition["nb_personnes"] = nb_personnes
            else:
                repartition["default"] = montant_total
        
        elif cle_repartition == CleRepartition.PAR_GROUPE:
            # Répartition par groupe : diviser par le nombre de groupes (utilise nombre_participants)
            projet = souscription.projet_voyage
            if projet:
                nb_groupes = max(1, (getattr(projet, 'nombre_participants', 1) or 1) // 4)  # Groupe de 4
                montant_par_groupe = montant_total / nb_groupes
                repartition["par_groupe"] = montant_par_groupe
                repartition["nb_groupes"] = nb_groupes
            else:
                repartition["default"] = montant_total
        
        elif cle_repartition == CleRepartition.PAR_DUREE:
            # Répartition par durée : calculer selon la durée en jours
            duree_jours = (souscription.date_fin - souscription.date_debut).days if souscription.date_fin else 30
            montant_par_jour = montant_total / duree_jours
            repartition["par_duree"] = montant_par_jour
            repartition["duree_jours"] = duree_jours
        
        elif cle_repartition == CleRepartition.PAR_DESTINATION:
            # Répartition par destination : selon la destination du voyage
            projet = souscription.projet_voyage
            if projet:
                destination = getattr(projet, 'destination', 'default')
                # Logique spécifique selon la destination
                repartition["destination"] = destination
                repartition["montant"] = montant_total
            else:
                repartition["default"] = montant_total
        
        return repartition
    
    @staticmethod
    def process_repartition(
        db: Session,
        souscription_id: int,
        paiement_id: int,
        account_id: int
    ) -> Repartition:
        """Traiter une répartition avec transactions ACID"""
        try:
            # Récupérer les données
            souscription = db.query(Souscription).filter(Souscription.id == souscription_id).first()
            paiement = db.query(Paiement).filter(Paiement.id == paiement_id).first()
            produit = db.query(ProduitAssurance).filter(
                ProduitAssurance.id == souscription.produit_assurance_id
            ).first()
            
            if not all([souscription, paiement, produit]):
                raise ValueError("Missing required data")
            
            # Calculer la répartition
            repartition_details = FinanceService.calculate_repartition(
                db=db,
                souscription_id=souscription_id,
                paiement_id=paiement_id,
                cle_repartition=produit.cle_repartition,
                montant_total=paiement.montant
            )
            
            # Créer l'enregistrement de répartition
            repartition = Repartition(
                souscription_id=souscription_id,
                paiement_id=paiement_id,
                produit_assurance_id=produit.id,
                montant_total=paiement.montant,
                cle_repartition=produit.cle_repartition.value,
                repartition_details=repartition_details,
                montant_par_personne=repartition_details.get("par_personne"),
                montant_par_groupe=repartition_details.get("par_groupe"),
                montant_par_duree=repartition_details.get("par_duree"),
                montant_par_destination=repartition_details.get("montant"),
                montant_fixe=repartition_details.get("default")
            )
            
            db.add(repartition)
            
            # Créer le mouvement financier
            reference = f"REP-{paiement_id}-{uuid.uuid4().hex[:8].upper()}"
            FinanceService.create_movement(
                db=db,
                account_id=account_id,
                movement_type="repartition",
                amount=paiement.montant,
                description=f"Répartition pour souscription {souscription.numero_souscription}",
                reference=reference,
                reference_type="repartition",
                related_id=repartition.id
            )
            
            db.commit()
            db.refresh(repartition)
            
            logger.info(f"Repartition processed: {repartition.id} for payment {paiement_id}")
            return repartition
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing repartition: {e}")
            raise
    
    @staticmethod
    def process_refund(
        db: Session,
        paiement_id: int,
        account_id: int,
        montant: Decimal,
        raison: str,
        processed_by: int
    ) -> Refund:
        """Traiter un remboursement avec transactions ACID"""
        try:
            paiement = db.query(Paiement).filter(Paiement.id == paiement_id).first()
            if not paiement:
                raise ValueError(f"Payment {paiement_id} not found")
            
            # Vérifier que le paiement peut être remboursé
            if paiement.statut != StatutPaiement.VALIDE:
                raise ValueError("Payment must be valid to refund")
            
            # Créer le remboursement
            reference_remboursement = f"REF-{paiement_id}-{uuid.uuid4().hex[:8].upper()}"
            refund = Refund(
                paiement_id=paiement_id,
                souscription_id=paiement.souscription_id,
                account_id=account_id,
                montant=montant,
                raison=raison,
                reference_remboursement=reference_remboursement,
                statut="processing",
                processed_by=processed_by
            )
            
            db.add(refund)
            
            # Créer le mouvement de crédit (remboursement)
            FinanceService.create_movement(
                db=db,
                account_id=account_id,
                movement_type="refund",
                amount=montant,
                description=f"Remboursement pour paiement {paiement.reference_transaction} - {raison}",
                reference=reference_remboursement,
                reference_type="refund",
                related_id=refund.id
            )
            
            # Mettre à jour le paiement
            paiement.statut = StatutPaiement.REMBOURSE
            paiement.montant_rembourse = montant
            
            # Mettre à jour le statut du remboursement
            refund.statut = "completed"
            refund.date_remboursement = datetime.utcnow()
            
            db.commit()
            db.refresh(refund)
            
            logger.info(f"Refund processed: {refund.id} for payment {paiement_id}")
            return refund
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing refund: {e}")
            raise
    
    @staticmethod
    def get_account_balance(db: Session, account_id: int) -> Decimal:
        """Obtenir le solde d'un compte"""
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")
        return account.balance

