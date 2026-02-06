from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.enums import Role, StatutSouscription
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
from typing import List

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
    Obtenir la liste des souscriptions en attente (pending).
    Accessible par admin, médecin et finance manager.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Limiter la limite maximale pour éviter les timeouts
    MAX_LIMIT = 500
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT
        logger.warning(f"Limite réduite à {MAX_LIMIT} pour éviter les timeouts")
    
    try:
        # Essayer de charger avec les relations
        try:
            souscriptions_query = (
                db.query(Souscription)
                .options(
                    selectinload(Souscription.produit_assurance),
                    selectinload(Souscription.projet_voyage),
                    selectinload(Souscription.user),
                )
                .filter(
                    Souscription.statut.in_([StatutSouscription.EN_ATTENTE, StatutSouscription.PENDING])
                )
                .order_by(Souscription.created_at.desc())
            )
        except Exception as e:
            # Si erreur avec selectinload, charger sans les relations
            logger.warning(f"Erreur lors du chargement des relations: {e}")
            souscriptions_query = (
                db.query(Souscription)
                .filter(
                    Souscription.statut.in_([StatutSouscription.EN_ATTENTE, StatutSouscription.PENDING])
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
    Workflow actuel : le médecin MH valide l'inscription (compte), pas la souscription.
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
    Approuver définitivement une souscription (agent de production MH).
    
    Workflow : l'agent de production valide la souscription pour produire l'attestation définitive.
    La validation médicale sur la souscription n'est plus requise (le médecin MH valide l'inscription, pas la souscription).
    """
    souscription = db.query(Souscription).filter(Souscription.id == subscription_id).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Mettre à jour la validation finale
    souscription.validation_finale = "approved" if validation.approved else "rejected"
    souscription.validation_finale_par = current_user.id
    souscription.validation_finale_date = datetime.utcnow()
    souscription.validation_finale_notes = validation.notes
    
    # Si approuvée, changer le statut de la souscription
    if validation.approved:
        souscription.statut = StatutSouscription.ACTIVE
    
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
        Paiement.statut == "valide"
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
    
    # Créer l'attestation définitive
    attestation = AttestationService.create_attestation_definitive(
        db=db,
        souscription=souscription,
        paiement=paiement,
        user=user
    )
    
    return {"url": attestation.url_signee, "attestation_id": attestation.id}
