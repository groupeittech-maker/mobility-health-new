"""
Service pour la gestion financière avec transactions ACID et anti-doublon
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
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
from app.models.courtier import Courtier
from app.models.assureur import Assureur
from app.core.enums import CleRepartition, StatutPaiement
from app.core.tarification_defaults import EKYC_FEE_PER_DOSSIER
from app.services.parametre_pays_service import get_reassureur

logger = logging.getLogger(__name__)


@dataclass
class LedgerRepartition:
    """Répartition comptable d'un encaissement souscription (tableau de répartition)."""

    assureur: Decimal = Decimal("0.00")  # Part assureur = participation % × Prime Nette
    courtier: Decimal = Decimal("0.00")
    courtier_id: Optional[int] = None
    courtier_nom: Optional[str] = None
    courtier_pct: Optional[Decimal] = None
    reassureur: Decimal = Decimal("0.00")  # Part réassureur (SCGRÉ ou autre, par pays)
    reassureur_nom: Optional[str] = None
    mhc: Decimal = Decimal("0.00")  # Part MHC nette (reliquat PN + chargements - eKYC)
    ekyc: Decimal = Decimal("0.00")  # Part partenaire eKYC (350 FCFA/dossier)


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
        currency: str = "XAF"
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

    # -----------------------------------------------------------------------
    # Partage comptable entre assuré/courtier/MH
    # (migré ici depuis app/api/v1/payments.py pour séparer paiement/comptabilité)
    # -----------------------------------------------------------------------
    @staticmethod
    def ledger_prime_and_frais_split(
        subscription: Optional[Souscription],
        montant_total: Decimal,
    ) -> Tuple[Decimal, Decimal]:
        """
        Répartition comptable des encaissements souscription : part assureur = Prime Nette
        (prime_assurance), Mobility Health = tout le chargement (Coût de Police + Taxe +
        taxes additionnelles) = montant total - Prime Nette.
        """
        mt = montant_total or Decimal("0.00")
        if not subscription:
            return mt.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), Decimal("0.00")

        prime = subscription.prime_assurance
        frais = subscription.frais_services

        if prime is not None and frais is not None:
            part_ass = Decimal(str(prime)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            part_mh = (mt - part_ass).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return part_ass, part_mh if part_mh > 0 else Decimal("0.00")

        if prime is not None:
            part_ass = Decimal(str(prime)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            part_mh = (mt - part_ass).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return part_ass, part_mh if part_mh > 0 else Decimal("0.00")

        if frais is not None:
            part_mh = Decimal(str(frais)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            part_ass = (mt - part_mh).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return part_ass if part_ass > 0 else Decimal("0.00"), part_mh

        # Anciennes souscriptions sans détail : tout le paiement compte comme prime assureur
        return mt.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), Decimal("0.00")

    @staticmethod
    def ledger_ekyc_share(
        subscription: Optional[Souscription],
        mh_share: Decimal,
    ) -> Decimal:
        """
        Part du partenaire eKYC (350 FCFA par dossier souscrit), prélevée
        sur la part MHC. 0 pour les anciennes souscriptions sans détail.
        """
        if not subscription or getattr(subscription, "prime_assurance", None) is None:
            return Decimal("0.00")
        mh = (mh_share or Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if mh <= Decimal("0.00"):
            return Decimal("0.00")
        return min(EKYC_FEE_PER_DOSSIER, mh)

    @staticmethod
    def ledger_repartition_complete(
        subscription: Optional[Souscription],
        montant_total: Decimal,
        db: Session,
        assureur_id: Optional[int] = None,
    ) -> LedgerRepartition:
        """
        Répartition selon le « Tableau de répartition » :

        - Canal assureur : assureur = participation % × PN (commission_assureur_pct du
          produit), réassureur = r % × PN, MHC = (100 − P − r) % × PN.
        - Canal courtier : courtier = C % × PN, puis reliquat → réassureur r %,
          MHC (100 − r) % du reliquat. Assureur = 0.
        - Chargements (Coût de Police + Taxe + taxes additionnelles) → MHC.
        - eKYC : 350 FCFA/dossier prélevés sur la part MHC.
        """
        rep = LedgerRepartition()
        mt = (montant_total or Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        pn_raw = getattr(subscription, "prime_assurance", None) if subscription else None
        if pn_raw is None:
            # Anciennes souscriptions sans détail : tout le paiement part à l'assureur
            rep.assureur = mt
            return rep

        pn = Decimal(str(pn_raw)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        chargements = (mt - pn).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if chargements < Decimal("0.00"):
            chargements = Decimal("0.00")

        # Réassureur du pays assureur (défaut SCGRÉ 10 %)
        pays_assureur = None
        if assureur_id:
            assureur_row = db.query(Assureur).filter(Assureur.id == assureur_id).first()
            pays_assureur = assureur_row.pays if assureur_row else None
        reassureur_nom, reassureur_pct = get_reassureur(db, pays_assureur)
        rep.reassureur_nom = reassureur_nom

        # Résolution du courtier (canal courtier)
        courtier = None
        courtier_id = getattr(subscription, "courtier_id", None)
        if courtier_id:
            courtier = db.query(Courtier).filter(Courtier.id == courtier_id).first()
        elif getattr(subscription, "canal_distribution", None) == "courtier" and assureur_id:
            # Fallback legacy : courtier unique rattaché à l'assureur
            matches = (
                db.query(Courtier)
                .filter(Courtier.assureur_id == assureur_id)
                .order_by(Courtier.id.asc())
                .all()
            )
            if matches:
                courtier = matches[0]
                if len(matches) > 1:
                    logger.warning(
                        "Plusieurs courtiers trouvés pour assureur_id=%s, fallback sur id=%s",
                        assureur_id,
                        courtier.id,
                    )

        if courtier:
            # Canal courtier : commission C % × PN, reliquat → réassureur r % / MHC reste
            c_pct = Decimal(str(courtier.commission_pct or Decimal("0.00")))
            rep.courtier = (pn * c_pct / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            rep.courtier_id = courtier.id
            rep.courtier_nom = courtier.nom
            rep.courtier_pct = c_pct
            reliquat = (pn - rep.courtier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            rep.reassureur = (reliquat * reassureur_pct / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            mh_pn = (reliquat - rep.reassureur).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            # Canal assureur : assureur P % × PN, réassureur r % × PN, MHC reste
            produit = None
            if getattr(subscription, "produit_assurance_id", None):
                produit = (
                    db.query(ProduitAssurance)
                    .filter(ProduitAssurance.id == subscription.produit_assurance_id)
                    .first()
                )
            participation_pct = Decimal("0.00")
            if produit is not None and produit.commission_assureur_pct is not None:
                participation_pct = Decimal(str(produit.commission_assureur_pct))
            rep.assureur = (pn * participation_pct / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            rep.reassureur = (pn * reassureur_pct / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            mh_pn = (pn - rep.assureur - rep.reassureur).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        mh_gross = (mh_pn + chargements).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rep.ekyc = FinanceService.ledger_ekyc_share(subscription, mh_gross)
        rep.mhc = (mh_gross - rep.ekyc).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return rep

    @staticmethod
    def refund_policy_breakdown(
        subscription: Optional[Souscription],
        montant_total: Decimal,
        refund_kind: str,
    ) -> Tuple[Decimal, Decimal]:
        """
        Retourne (montant_rembourse_assure, montant_conserve_mh).

        Règles métier:
        - refus dossier: assureur + courtier remboursent intégralement, MH conserve ses frais de service.
        - résiliation: assureur + courtier remboursent intégralement, MH perçoit 30 % de la prime.
        """
        mt = (montant_total or Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        prime_share, _ = FinanceService.ledger_prime_and_frais_split(
            subscription, mt
        )

        has_explicit_breakdown = bool(
            subscription
            and (
                getattr(subscription, "prime_assurance", None) is not None
                or getattr(subscription, "frais_services", None) is not None
            )
        )

        if refund_kind == "resiliation":
            mh_retained = (prime_share * Decimal("0.30")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            if has_explicit_breakdown:
                # MHC conserve ses chargements propres : « Taxe » (frais de service)
                # + Coût de Police. Les taxes additionnelles sont remboursées.
                mh_retained = (
                    Decimal(str(getattr(subscription, "frais_services", None) or 0))
                    + Decimal(str(getattr(subscription, "cout_police", None) or 0))
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                mh_retained = (mt * Decimal("0.10")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

        if mh_retained < Decimal("0.00"):
            mh_retained = Decimal("0.00")
        if mh_retained > mt:
            mh_retained = mt

        insured_refund = (mt - mh_retained).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return insured_refund, mh_retained

