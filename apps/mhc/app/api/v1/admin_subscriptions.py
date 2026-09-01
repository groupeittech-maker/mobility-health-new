from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.config import settings
from app.core.enums import Role, StatutSouscription, StatutPaiement
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.souscription import Souscription
from app.models.questionnaire import Questionnaire
from app.models.paiement import Paiement
from app.models.attestation import Attestation
from app.schemas.souscription import SouscriptionResponse
from app.schemas.questionnaire import QuestionnaireResponse
from app.schemas.paiement import PaiementResponse
from app.services.attestation_service import AttestationService
from pydantic import BaseModel
from app.core.security import create_download_access_token

router = APIRouter()


def require_role(allowed_roles: List[Role]):
    """Dependency factory pour vérifier les rôles"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Gérer le cas où role peut être un enum ou une chaîne
        current_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        allowed_role_values = [r.value if hasattr(r, 'value') else str(r) for r in allowed_roles]
        
        if current_role not in allowed_role_values and current_role != Role.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required roles: {allowed_role_values}"
            )
        return current_user
    return role_checker


class ValidationRequest(BaseModel):
    """Schéma pour les validations"""
    approved: bool
    notes: Optional[str] = None


@router.get("/pending", response_model=List[SouscriptionResponse])
async def get_pending_subscriptions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([
        Role.DOCTOR,
        Role.FINANCE_MANAGER,
        Role.MEDICAL_REVIEWER,
        Role.TECHNICAL_REVIEWER,
        Role.PRODUCTION_AGENT
    ]))
):
    """
    Souscriptions en attente de validation par l'agent de production.
    Critères : paiement valide + validation_finale non encore effectuée.
    L'attestation provisoire est générée à la création du paiement ;
    l'attestation définitive et la e-carte sont créées à la validation production.
    En cas de refus définitif : souscription résiliée et remboursement au client de 90 % du montant
    payé (10 % de retenue frais Mobility Health), si un paiement valide existe.
    """
    import logging

    logger = logging.getLogger(__name__)
    
    MAX_LIMIT = 500
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT
        logger.warning(f"Limite réduite à {MAX_LIMIT} pour éviter les timeouts")
    
    try:
        from sqlalchemy import exists, select
        from sqlalchemy.sql import or_

        paiement_valide_subq = (
            select(Paiement.id)
            .where(Paiement.souscription_id == Souscription.id)
            .where(Paiement.statut == StatutPaiement.VALIDE.name)
            .correlate(Souscription)
        )
        validation_finale_pending = or_(
            Souscription.validation_finale.is_(None),
            Souscription.validation_finale == "",
            Souscription.validation_finale.in_(["pending", "en_attente"]),
        )
        # Avis médical rendu (favorable ou défavorable) : l'agent de production statue en dernier.
        # Tant que validation_medicale est vide/pending, le dossier reste côté validateur médical.
        validation_medicale_terminee = Souscription.validation_medicale.in_(["approved", "rejected"])
        try:
            souscriptions_query = (
                db.query(Souscription)
                .options(
                    selectinload(Souscription.produit_assurance),
                    selectinload(Souscription.projet_voyage),
                    selectinload(Souscription.user),
                )
                .filter(
                    exists(paiement_valide_subq),
                    validation_medicale_terminee,
                    validation_finale_pending,
                )
                .order_by(Souscription.created_at.desc())
            )
        except Exception as e:
            logger.warning(f"Erreur lors du chargement des relations: {e}")
            souscriptions_query = (
                db.query(Souscription)
                .filter(
                    exists(paiement_valide_subq),
                    validation_medicale_terminee,
                    validation_finale_pending,
                )
                .order_by(Souscription.created_at.desc())
            )
        
        souscriptions = (
            souscriptions_query
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        # Sérialiser avec gestion d'erreur individuelle
        result = []
        for souscription in souscriptions:
            try:
                result.append(SouscriptionResponse.model_validate(souscription))
            except Exception as ser_error:
                logger.warning(f"Erreur lors de la sérialisation de la souscription {souscription.id}: {ser_error}")
                # Continuer avec les autres souscriptions
        
        return result
            
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des souscriptions en attente: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des souscriptions: {str(e)}"
        )


@router.post("/{subscription_id}/validate_medical", response_model=SouscriptionResponse)
async def validate_medical(
    subscription_id: int,
    validation: ValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.DOCTOR]))
):
    """
    Valider médicalement une souscription (legacy / optionnel).
    L'inscription (compte) s'active par vérification e-mail ; ce endpoint concerne la souscription.
    La souscription est validée par l'agent de production (validate_finale).
    """
    souscription = db.query(Souscription).filter(Souscription.id == subscription_id).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Mettre à jour la validation médicale
    souscription.validation_medicale = "approved" if validation.approved else "rejected"
    souscription.validation_medicale_par = current_user.id
    souscription.validation_medicale_date = datetime.utcnow()
    souscription.validation_medicale_notes = validation.notes
    
    # Notifier l'utilisateur du résultat de la validation médicale
    from app.models.notification import Notification
    from app.models.user import User
    user = db.query(User).filter(User.id == souscription.user_id).first()
    
    if user:
        if validation.approved:
            message = f"📋 Informations:\n• Votre prise en charge pour la souscription #{souscription.numero_souscription} a été validée par le médecin référent MH.\n• Votre dossier est en cours de traitement."
            if validation.notes:
                message += f"\n• Notes du médecin: {validation.notes}"
        else:
            message = f"📋 Informations:\n• Votre prise en charge pour la souscription #{souscription.numero_souscription} a été refusée par le médecin référent MH."
            if validation.notes:
                message += f"\n• Motif du refus: {validation.notes}"
            else:
                message += "\n• Veuillez contacter le service client pour plus d'informations."
        
        notification = Notification(
            user_id=user.id,
            type_notification="medical_validation_result",
            titre="Résultat de la validation médicale",
            message=message,
            lien_relation_id=souscription.id,
            lien_relation_type="souscription"
        )
        db.add(notification)
    
    db.commit()
    db.refresh(souscription)
    
    return souscription


@router.post("/{subscription_id}/validate_tech", response_model=SouscriptionResponse)
async def validate_tech(
    subscription_id: int,
    validation: ValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.FINANCE_MANAGER, Role.TECHNICAL_REVIEWER, Role.HOSPITAL_ADMIN]))
):
    """
    Valider techniquement une souscription.
    Accessible par les agents techniques (finance_manager) et admins.
    """
    souscription = db.query(Souscription).filter(Souscription.id == subscription_id).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Mettre à jour la validation technique
    souscription.validation_technique = "approved" if validation.approved else "rejected"
    souscription.validation_technique_par = current_user.id
    souscription.validation_technique_date = datetime.utcnow()
    souscription.validation_technique_notes = validation.notes
    
    db.commit()
    db.refresh(souscription)
    
    return souscription


@router.post("/{subscription_id}/approve_final", response_model=SouscriptionResponse)
async def approve_final(
    subscription_id: int,
    validation: ValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.PRODUCTION_AGENT]))
):
    """
    Approuver ou refuser définitivement une souscription (agent de production MH).

    Après un avis médical (favorable ou défavorable), l'agent statue en dernier.
    Approbation : attestation définitive et e-carte si besoin.
    Refus définitif : résiliation, ligne de validation production sur l'attestation provisoire,
    remboursement automatique de 90 % du prix appliqué au client (10 % retenue frais MH) si paiement valide.
    """
    import logging
    from app.models.paiement import Paiement
    from app.models.attestation import Attestation
    from app.models.validation_attestation import ValidationAttestation
    from app.core.enums import StatutPaiement
    from app.services.attestation_service import AttestationService

    logger = logging.getLogger(__name__)
    souscription = db.query(Souscription).options(
        selectinload(Souscription.user),
        selectinload(Souscription.produit_assurance),
        selectinload(Souscription.projet_voyage),
    ).filter(Souscription.id == subscription_id).first()

    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )

    souscription.validation_finale = "approved" if validation.approved else "rejected"
    souscription.validation_finale_par = current_user.id
    souscription.validation_finale_date = datetime.utcnow()
    souscription.validation_finale_notes = validation.notes

    if validation.approved:
        souscription.statut = StatutSouscription.ACTIVE

        attestation_provisoire = db.query(Attestation).filter(
            Attestation.souscription_id == subscription_id,
            Attestation.type_attestation == "provisoire",
        ).first()

        if not attestation_provisoire:
            paiement = db.query(Paiement).filter(
                Paiement.souscription_id == subscription_id,
                Paiement.statut == StatutPaiement.VALIDE.name,
            ).order_by(Paiement.created_at.desc()).first()
            user = souscription.user
            if paiement and user:
                try:
                    attestation_provisoire = AttestationService.create_attestation_provisoire(
                        db=db,
                        souscription=souscription,
                        paiement=paiement,
                        user=user,
                    )
                    db.flush()
                    logger.info("Attestation provisoire créée pour souscription %s (ID %s)", souscription.numero_souscription, subscription_id)
                except Exception as e:
                    logger.exception("Erreur création attestation provisoire: %s", e)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Erreur lors de la création de l'attestation provisoire: {str(e)}",
                    )
            else:
                logger.warning("Souscription %s approuvée sans paiement valide - attestation non créée", subscription_id)

        if attestation_provisoire:
            validation_prod = db.query(ValidationAttestation).filter(
                ValidationAttestation.attestation_id == attestation_provisoire.id,
                ValidationAttestation.type_validation.in_(["production", "agpmh"]),
            ).first()
            if not validation_prod:
                validation_prod = ValidationAttestation(
                    attestation_id=attestation_provisoire.id,
                    type_validation="production",
                    est_valide=True,
                    valide_par_user_id=current_user.id,
                    date_validation=datetime.utcnow(),
                )
                db.add(validation_prod)
                db.flush()

            existing_definitive = db.query(Attestation).filter(
                Attestation.souscription_id == subscription_id,
                Attestation.type_attestation == "definitive",
            ).first()
            if not existing_definitive:
                paiement = db.query(Paiement).filter(
                    Paiement.souscription_id == subscription_id,
                    Paiement.statut == StatutPaiement.VALIDE.name,
                ).order_by(Paiement.created_at.desc()).first()
                user = souscription.user
                if paiement and user:
                    try:
                        existing_definitive = AttestationService.create_attestation_definitive(
                            db=db,
                            souscription=souscription,
                            paiement=paiement,
                            user=user,
                        )
                        db.flush()
                        logger.info("Attestation définitive créée pour souscription %s", souscription.numero_souscription)
                    except ValueError as e:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e),
                        )
                    except Exception as e:
                        logger.exception("Erreur création attestation définitive: %s", e)
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Erreur lors de la création de l'attestation définitive: {str(e)}",
                        )

    else:
        # Refus définitif : résiliation + trace validation production + remboursement
        # intégral de la prime (assureur + courtier), MH conservant uniquement les frais de service.
        souscription.statut = StatutSouscription.RESILIEE
        attestation_provisoire = db.query(Attestation).filter(
            Attestation.souscription_id == subscription_id,
            Attestation.type_attestation == "provisoire",
        ).first()
        if attestation_provisoire:
            validation_prod = db.query(ValidationAttestation).filter(
                ValidationAttestation.attestation_id == attestation_provisoire.id,
                ValidationAttestation.type_validation.in_(["production", "agpmh"]),
            ).first()
            if not validation_prod:
                validation_prod = ValidationAttestation(
                    attestation_id=attestation_provisoire.id,
                    type_validation="production",
                    est_valide=False,
                    commentaires=validation.notes,
                    valide_par_user_id=current_user.id,
                    date_validation=None,
                )
                db.add(validation_prod)
            else:
                validation_prod.est_valide = False
                validation_prod.commentaires = validation.notes
                validation_prod.valide_par_user_id = current_user.id
                validation_prod.date_validation = None

        import uuid
        from decimal import Decimal

        from app.models.finance_account import Account
        from app.services.finance_service import FinanceService

        try:
            paiement = (
                db.query(Paiement)
                .filter(Paiement.souscription_id == souscription.id)
                .filter(Paiement.statut == StatutPaiement.VALIDE.name)
                .order_by(Paiement.created_at.desc())
                .first()
            )
            if paiement is not None and souscription.prix_applique is not None:
                base = Decimal(str(souscription.prix_applique))
                frais = getattr(souscription, "frais_services", None)
                if frais is not None:
                    retenue_mh = Decimal(str(frais)).quantize(Decimal("0.01"))
                elif getattr(souscription, "prime_assurance", None) is not None:
                    retenue_mh = (base - Decimal(str(souscription.prime_assurance))).quantize(Decimal("0.01"))
                else:
                    # Repli legacy si le détail prime/frais n'existe pas encore.
                    retenue_mh = (base * Decimal("0.10")).quantize(Decimal("0.01"))
                if retenue_mh < Decimal("0.00"):
                    retenue_mh = Decimal("0.00")
                if retenue_mh > base:
                    retenue_mh = base
                montant_remboursement = (base - retenue_mh).quantize(Decimal("0.01"))
                account = (
                    db.query(Account)
                    .filter(Account.owner_id == souscription.user_id)
                    .filter(Account.account_type == "client")
                    .first()
                )
                if not account:
                    account_number = f"CLIENT-{souscription.user_id}-{uuid.uuid4().hex[:8].upper()}"
                    account = Account(
                        account_number=account_number,
                        account_name=f"Compte client - {souscription.user_id}",
                        account_type="client",
                        balance=Decimal("0.00"),
                        currency="XAF",
                        is_active=True,
                        owner_id=souscription.user_id,
                    )
                    db.add(account)
                    db.flush()
                    logger.info("Compte client %s créé pour remboursement refus production", account.id)
                raison = (
                    f"Refus définitif production — souscription {souscription.numero_souscription or souscription.id} "
                    f"(prime remboursée au client, frais de service MH conservés: {retenue_mh} XAF)"
                )
                if validation.notes:
                    raison += f" — {validation.notes}"
                FinanceService.process_refund(
                    db=db,
                    paiement_id=paiement.id,
                    account_id=account.id,
                    montant=montant_remboursement,
                    raison=raison,
                    processed_by=current_user.id,
                )
                logger.info(
                    "Refus production : remboursement %s XAF (retenue MH %s sur %s) souscription %s",
                    montant_remboursement,
                    retenue_mh,
                    base,
                    souscription.id,
                )
            else:
                logger.warning(
                    "Refus production souscription %s : pas de remboursement (paiement valide ou prix_applique absent)",
                    souscription.id,
                )
        except Exception as e:
            logger.exception("Erreur remboursement refus production souscription %s: %s", souscription.id, e)

    db.commit()
    db.refresh(souscription)
    return souscription


@router.get("/", response_model=List[SouscriptionResponse])
async def get_all_subscriptions(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([
        Role.DOCTOR,
        Role.FINANCE_MANAGER,
        Role.MEDICAL_REVIEWER,
        Role.TECHNICAL_REVIEWER,
        Role.PRODUCTION_AGENT
    ]))
):
    """Obtenir toutes les souscriptions (admin, médecin, agent technique)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Essayer de charger avec les relations
        try:
            query = db.query(Souscription).options(
                selectinload(Souscription.produit_assurance),
                selectinload(Souscription.projet_voyage),
                selectinload(Souscription.user),
            )
        except Exception as e:
            logger.warning(f"Erreur lors du chargement des relations: {e}")
            query = db.query(Souscription)
        
        if statut:
            query = query.filter(Souscription.statut == statut)
        
        souscriptions = query.order_by(Souscription.created_at.desc()).offset(skip).limit(limit).all()
        return souscriptions
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des souscriptions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des souscriptions: {str(e)}"
        )


@router.get("/{subscription_id}", response_model=SouscriptionResponse)
async def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([
        Role.DOCTOR,
        Role.FINANCE_MANAGER,
        Role.MEDICAL_REVIEWER,
        Role.TECHNICAL_REVIEWER,
        Role.PRODUCTION_AGENT
    ]))
):
    """Obtenir une souscription par ID (admin, médecin, agent technique)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Essayer de charger avec les relations
        try:
            souscription = (
                db.query(Souscription)
                .options(
                    selectinload(Souscription.produit_assurance),
                    selectinload(Souscription.projet_voyage),
                )
                .filter(Souscription.id == subscription_id)
                .first()
            )
        except Exception as e:
            logger.warning(f"Erreur lors du chargement des relations: {e}")
            souscription = (
                db.query(Souscription)
                .filter(Souscription.id == subscription_id)
                .first()
            )
        
        if not souscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Souscription non trouvée"
            )
        
        return souscription
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la souscription {subscription_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de la souscription: {str(e)}"
        )


@router.get("/{subscription_id}/dossier")
async def get_subscription_dossier(
    request: Request,
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.PRODUCTION_AGENT, Role.ADMIN]))
):
    """
    Dossier complet d'une souscription pour l'agent de production.
    Retourne questionnaires, documents, données civiles/médicales (même format que validation inscription).
    """
    from app.api.v1.attestations import (
        _collect_latest_questionnaires,
        _serialize_questionnaires,
        _serialize_document_for_review,
        _to_float_or_none,
        _is_internal_minio_url,
        _build_projet_document_proxy_url,
        _get_ecard_public_base,
    )
    from app.schemas.attestation import AttestationReviewItem, DocumentReviewInline, QuestionnaireInline, ValidationState
    from app.models.projet_voyage import ProjetVoyage
    from app.models.projet_voyage_document import ProjetVoyageDocument
    from app.models.destination import DestinationCountry

    souscription = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.user),
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
        )
        .filter(Souscription.id == subscription_id)
        .first()
    )
    if not souscription:
        raise HTTPException(status_code=404, detail="Souscription non trouvée")

    attestation = (
        db.query(Attestation)
        .filter(
            Attestation.souscription_id == subscription_id,
            Attestation.type_attestation == "provisoire",
        )
        .order_by(Attestation.created_at.desc())
        .first()
    )
    attestation_download_url = None
    if attestation:
        attestation_token = create_download_access_token("attestation_pdf", attestation.id)
        attestation_download_url = f"/api/v1/attestations/{attestation.id}/download?token={attestation_token}"

    questionnaires_map = _collect_latest_questionnaires(db, [subscription_id])
    questionnaires_payload = _serialize_questionnaires(subscription_id, questionnaires_map)
    validation_states = {
        "medecin": ValidationState(
            status=getattr(souscription, "validation_medicale", None) or "pending",
            notes=getattr(souscription, "validation_medicale_notes", None),
            reviewer_id=getattr(souscription, "validation_medicale_par", None),
            decided_at=getattr(souscription, "validation_medicale_date", None),
        ),
        "technique": ValidationState(
            status=getattr(souscription, "validation_technique", None) or "pending",
            notes=getattr(souscription, "validation_technique_notes", None),
            reviewer_id=getattr(souscription, "validation_technique_par", None),
            decided_at=getattr(souscription, "validation_technique_date", None),
        ),
        "production": ValidationState(
            status=getattr(souscription, "validation_finale", None) or "pending",
            notes=getattr(souscription, "validation_finale_notes", None),
            reviewer_id=getattr(souscription, "validation_finale_par", None),
            decided_at=getattr(souscription, "validation_finale_date", None),
        ),
    }
    current_state = validation_states.get("production") or validation_states.get("agpmh")
    validation_status = (current_state.status if current_state else "pending")

    client = souscription.user
    produit = getattr(souscription, "produit_assurance", None)
    medical_reviewer = None
    if getattr(souscription, "validation_medicale_par", None):
        medical_reviewer = db.query(User).filter(User.id == souscription.validation_medicale_par).first()
    projet = None
    destination_country = None
    if souscription.projet_voyage_id:
        projet = db.query(ProjetVoyage).filter(ProjetVoyage.id == souscription.projet_voyage_id).first()
        if projet and getattr(projet, "destination_country_id", None):
            destination_country = db.query(DestinationCountry).filter(
                DestinationCountry.id == projet.destination_country_id
            ).first()

    is_tier_subscription = False
    tier_info = {}
    if projet and projet.notes and ("pour un tiers" in (projet.notes or "").lower()):
        is_tier_subscription = True
    if souscription.notes and ("pour un tiers" in (souscription.notes or "").lower()):
        is_tier_subscription = True
    if is_tier_subscription:
        tier_info = AttestationService._extract_traveler_info(db, souscription.id)
        if not tier_info.get("fullName") and projet and projet.notes:
            tier_info = AttestationService._extract_tier_info_from_notes(projet.notes)
        if not tier_info.get("fullName") and souscription.notes:
            tier_info = AttestationService._extract_tier_info_from_notes(souscription.notes)

    documents_projet_voyage = []
    if souscription.projet_voyage_id:
        docs = (
            db.query(ProjetVoyageDocument)
            .filter(ProjetVoyageDocument.projet_voyage_id == souscription.projet_voyage_id)
            .order_by(ProjetVoyageDocument.uploaded_at.desc())
            .all()
        )
        documents_projet_voyage = [_serialize_document_for_review(d) for d in docs]
        # Contourner minio:9000 : utiliser la base API (env ou déduite de la requête) pour le proxy
        try:
            base = _get_ecard_public_base(request).rstrip("/")
        except TypeError:
            base = _get_ecard_public_base().rstrip("/")
        if base:
            def _doc_proxy_url(doc_id: int) -> str:
                doc_token = create_download_access_token("project_document", doc_id)
                try:
                    base_url = _build_projet_document_proxy_url(doc_id, request)
                except TypeError:
                    base_url = _build_projet_document_proxy_url(doc_id)
                separator = "&" if "?" in base_url else "?"
                return f"{base_url}{separator}token={doc_token}"

            documents_projet_voyage = [
                d.model_copy(update={"download_url": _doc_proxy_url(d.id)})
                if d.download_url
                else d
                for d in documents_projet_voyage
            ]

    minors_info = AttestationService._extract_minors_from_notes(souscription.notes or "")
    if not minors_info and projet and getattr(projet, "notes", None):
        minors_info = AttestationService._extract_minors_from_notes(projet.notes)

    statut_val = souscription.statut
    statut_str = statut_val.value if hasattr(statut_val, "value") else str(statut_val)

    return AttestationReviewItem(
        attestation_id=attestation.id if attestation else 0,
        attestation_type=attestation.type_attestation if attestation else "provisoire",
        numero_attestation=attestation.numero_attestation if attestation else f"ATT-{souscription.numero_souscription}",
        attestation_download_url=attestation_download_url,
        attestation_created_at=attestation.created_at if attestation else souscription.created_at,
        souscription_id=souscription.id,
        numero_souscription=souscription.numero_souscription,
        souscription_status=statut_str,
        prix_applique=_to_float_or_none(souscription.prix_applique),
        currency=(getattr(produit, "currency", None) or "XAF") if produit else "XAF",
        date_debut=souscription.date_debut,
        date_fin=souscription.date_fin,
        travel_destination_city=(projet.destination if projet else None),
        travel_destination_country=(destination_country.nom if destination_country else None),
        client_id=client.id if client else None,
        client_name=(client.full_name or client.username) if client else None,
        client_email=client.email if client else None,
        client_date_naissance=client.date_naissance if client else None,
        client_telephone=client.telephone if client else None,
        client_sexe=client.sexe if client else None,
        client_nationalite=client.nationalite if client else None,
        client_numero_passeport=client.numero_passeport if client else None,
        client_validite_passeport=client.validite_passeport if client else None,
        client_pays_residence=client.pays_residence if client else None,
        client_contact_urgence=client.contact_urgence if client else None,
        client_maladies_chroniques=getattr(client, "maladies_chroniques", None) if client else None,
        client_traitements_en_cours=getattr(client, "traitements_en_cours", None) if client else None,
        client_antecedents_recents=getattr(client, "antecedents_recents", None) if client else None,
        client_grossesse=getattr(client, "grossesse", None) if client else None,
        produit_nom=produit.nom if produit else None,
        medical_validation_reviewer_name=(medical_reviewer.full_name or medical_reviewer.username) if medical_reviewer else None,
        is_tier_subscription=is_tier_subscription,
        tier_full_name=tier_info.get("fullName") if tier_info else None,
        tier_birth_date=tier_info.get("birthDate") if tier_info else None,
        tier_gender=tier_info.get("gender") if tier_info else None,
        tier_nationality=tier_info.get("nationality") if tier_info else None,
        tier_passport_number=tier_info.get("passportNumber") if tier_info else None,
        tier_passport_expiry_date=tier_info.get("passportExpiryDate") if tier_info else None,
        tier_phone=tier_info.get("phone") if tier_info else None,
        tier_email=tier_info.get("email") if tier_info else None,
        tier_address=tier_info.get("address") if tier_info else None,
        validation_type="production",
        validation_status=validation_status,
        validations=validation_states,
        questionnaires=questionnaires_payload,
        documents_projet_voyage=documents_projet_voyage or None,
        minors_info=minors_info or None,
    )


@router.get("/{subscription_id}/questionnaires", response_model=List[QuestionnaireResponse])
async def get_subscription_questionnaires(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([
        Role.DOCTOR,
        Role.FINANCE_MANAGER,
        Role.MEDICAL_REVIEWER,
        Role.TECHNICAL_REVIEWER,
        Role.PRODUCTION_AGENT
    ]))
):
    """Obtenir tous les questionnaires d'une souscription"""
    # Vérifier que la souscription existe
    souscription = db.query(Souscription).filter(Souscription.id == subscription_id).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Récupérer tous les questionnaires
    questionnaires = db.query(Questionnaire).filter(
        Questionnaire.souscription_id == subscription_id
    ).order_by(Questionnaire.type_questionnaire, Questionnaire.version.desc()).all()
    
    return questionnaires


@router.get("/{subscription_id}/payments", response_model=List[PaiementResponse])
async def get_subscription_payments(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([
        Role.DOCTOR,
        Role.FINANCE_MANAGER,
        Role.MEDICAL_REVIEWER,
        Role.TECHNICAL_REVIEWER,
        Role.PRODUCTION_AGENT
    ]))
):
    """Obtenir tous les paiements d'une souscription"""
    # Vérifier que la souscription existe
    souscription = db.query(Souscription).filter(Souscription.id == subscription_id).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Récupérer tous les paiements
    paiements = db.query(Paiement).filter(
        Paiement.souscription_id == subscription_id
    ).order_by(Paiement.created_at.desc()).all()
    
    return paiements


@router.post("/{subscription_id}/generate-attestation")
async def generate_attestation(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN, Role.PRODUCTION_AGENT]))
):
    """Générer l'attestation définitive PDF pour une souscription (admin ou agent de production)"""
    souscription = db.query(Souscription).filter(Souscription.id == subscription_id).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier que la souscription est validée
    if souscription.validation_finale != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La souscription doit être validée avant de générer l'attestation définitive"
        )
    
    # Récupérer le paiement
    paiement = db.query(Paiement).filter(
        Paiement.souscription_id == subscription_id,
        Paiement.statut == StatutPaiement.VALIDE.name
    ).order_by(Paiement.created_at.desc()).first()
    
    if not paiement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun paiement valide trouvé pour cette souscription"
        )
    
    # Récupérer l'utilisateur
    user = db.query(User).filter(User.id == souscription.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Vérifier si une attestation définitive existe déjà
    existing_attestation = db.query(Attestation).filter(
        Attestation.souscription_id == subscription_id,
        Attestation.type_attestation == "definitive"
    ).first()
    
    if existing_attestation:
        # Rafraîchir l'URL
        from datetime import timedelta
        url_signee = AttestationService.refresh_signed_url(
            db=db,
            attestation=existing_attestation,
            expires=timedelta(hours=24),
            refresh_card=True
        )
        return {"url": url_signee, "attestation_id": existing_attestation.id}
    
    try:
        attestation = AttestationService.create_attestation_definitive(
            db=db,
            souscription=souscription,
            paiement=paiement,
            user=user,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {"url": attestation.url_signee, "attestation_id": attestation.id}


@router.post("/{subscription_id}/regenerate-ecard")
async def regenerate_subscription_ecard(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN, Role.PRODUCTION_AGENT])),
):
    """
    Regénère le fichier PNG de la e-carte pour l'attestation définitive de la souscription
    (photo + QR à jour). Utile si la carte avait été créée sans photo ou après correctifs backend.
    """
    import logging

    log = logging.getLogger(__name__)
    souscription = db.query(Souscription).filter(Souscription.id == subscription_id).first()
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée",
        )
    attestation = (
        db.query(Attestation)
        .filter(
            Attestation.souscription_id == subscription_id,
            Attestation.type_attestation == "definitive",
        )
        .order_by(Attestation.created_at.desc())
        .first()
    )
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune attestation définitive pour cette souscription",
        )
    result = AttestationService.regenerate_ecard_for_definitive(
        db=db,
        attestation=attestation,
        souscription=souscription,
    )
    if result.get("error"):
        log.error("regenerate-ecard souscription %s: %s", subscription_id, result["error"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )
    msg = "Carte numérique régénérée."
    log.info(
        "regenerate-ecard OK souscription=%s attestation=%s photo_bytes=%s",
        subscription_id,
        attestation.id,
        result.get("photo_bytes"),
    )
    return {
        "subscription_id": subscription_id,
        "attestation_id": attestation.id,
        "photo_bytes": result.get("photo_bytes", 0),
        "carte_url_preview": result.get("carte_url_preview"),
        "message": msg,
    }
