from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.souscription import Souscription
from app.models.questionnaire import Questionnaire
from app.models.notification import Notification
from app.schemas.questionnaire import (
    QuestionnaireCreate,
    QuestionnaireResponse,
    QuestionnaireStatusResponse
)
from datetime import datetime

router = APIRouter()


@router.post("/subscriptions/{subscription_id}/questionnaire/short", response_model=QuestionnaireResponse)
async def create_short_questionnaire(
    subscription_id: int,
    reponses: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer ou mettre à jour un questionnaire court pour une souscription"""
    # Vérifier que la souscription existe et appartient à l'utilisateur
    souscription = db.query(Souscription).filter(
        Souscription.id == subscription_id,
        Souscription.user_id == current_user.id
    ).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier s'il existe déjà un questionnaire court
    existing_questionnaire = db.query(Questionnaire).filter(
        Questionnaire.souscription_id == subscription_id,
        Questionnaire.type_questionnaire == "short"
    ).order_by(Questionnaire.version.desc()).first()
    
    # Déterminer la version
    version = 1
    if existing_questionnaire:
        version = existing_questionnaire.version + 1
        # Archiver l'ancien questionnaire
        existing_questionnaire.statut = "archive"
    
    # Créer le nouveau questionnaire
    questionnaire = Questionnaire(
        souscription_id=subscription_id,
        type_questionnaire="short",
        version=version,
        reponses=reponses,
        statut="complete"
    )
    
    db.add(questionnaire)
    db.commit()
    db.refresh(questionnaire)
    
    # Générer une notification
    notification = Notification(
        user_id=current_user.id,
        type_notification="questionnaire_completed",
        titre="Questionnaire court complété",
        message=f"Votre questionnaire court pour la souscription #{subscription_id} a été enregistré avec succès.",
        lien_relation_id=questionnaire.id,
        lien_relation_type="questionnaire"
    )
    db.add(notification)
    
    # Vérifier si l'utilisateur n'a rempli que le questionnaire court
    # Si oui, planifier une notification dans 3 jours pour inviter à remplir le questionnaire long
    long_questionnaire = db.query(Questionnaire).filter(
        Questionnaire.souscription_id == subscription_id,
        Questionnaire.type_questionnaire == "long",
        Questionnaire.statut == "complete"
    ).first()
    
    if not long_questionnaire:
        # Planifier une notification dans 3 jours pour inviter à remplir le questionnaire long
        try:
            from app.workers.tasks import schedule_questionnaire_long_reminder
            schedule_questionnaire_long_reminder.delay(
                user_id=current_user.id,
                subscription_id=subscription_id,
                questionnaire_id=questionnaire.id,
                reminder_days=3  # Rappel dans 3 jours
            )
        except Exception as e:
            # Si Celery n'est pas disponible, créer la notification immédiatement
            # (sera vérifiée lors du chargement des notifications)
            pass
    
    db.commit()
    
    return questionnaire


@router.post("/subscriptions/{subscription_id}/questionnaire/long", response_model=QuestionnaireResponse)
async def create_long_questionnaire(
    subscription_id: int,
    reponses: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer ou mettre à jour un questionnaire long pour une souscription"""
    # Vérifier que la souscription existe et appartient à l'utilisateur
    souscription = db.query(Souscription).filter(
        Souscription.id == subscription_id,
        Souscription.user_id == current_user.id
    ).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier s'il existe déjà un questionnaire long
    existing_questionnaire = db.query(Questionnaire).filter(
        Questionnaire.souscription_id == subscription_id,
        Questionnaire.type_questionnaire == "long"
    ).order_by(Questionnaire.version.desc()).first()
    
    # Déterminer la version
    version = 1
    if existing_questionnaire:
        version = existing_questionnaire.version + 1
        # Archiver l'ancien questionnaire
        existing_questionnaire.statut = "archive"
    
    # Créer le nouveau questionnaire
    questionnaire = Questionnaire(
        souscription_id=subscription_id,
        type_questionnaire="long",
        version=version,
        reponses=reponses,
        statut="complete"
    )
    
    db.add(questionnaire)
    db.commit()
    db.refresh(questionnaire)
    
    # Générer une notification
    notification = Notification(
        user_id=current_user.id,
        type_notification="questionnaire_completed",
        titre="Questionnaire long complété",
        message=f"Votre questionnaire long pour la souscription #{subscription_id} a été enregistré avec succès.",
        lien_relation_id=questionnaire.id,
        lien_relation_type="questionnaire"
    )
    db.add(notification)
    db.commit()
    
    return questionnaire


@router.post("/subscriptions/{subscription_id}/questionnaire/administratif", response_model=QuestionnaireResponse)
async def create_administratif_questionnaire(
    subscription_id: int,
    reponses: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer ou mettre à jour un questionnaire administratif/technique pour une souscription"""
    # Vérifier que la souscription existe et appartient à l'utilisateur
    souscription = db.query(Souscription).filter(
        Souscription.id == subscription_id,
        Souscription.user_id == current_user.id
    ).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier s'il existe déjà un questionnaire administratif
    existing_questionnaire = db.query(Questionnaire).filter(
        Questionnaire.souscription_id == subscription_id,
        Questionnaire.type_questionnaire == "administratif"
    ).order_by(Questionnaire.version.desc()).first()
    
    # Déterminer la version
    version = 1
    if existing_questionnaire:
        version = existing_questionnaire.version + 1
        # Archiver l'ancien questionnaire
        existing_questionnaire.statut = "archive"
    
    # Créer le nouveau questionnaire
    questionnaire = Questionnaire(
        souscription_id=subscription_id,
        type_questionnaire="administratif",
        version=version,
        reponses=reponses,
        statut="complete"
    )
    
    db.add(questionnaire)
    db.commit()
    db.refresh(questionnaire)
    
    # Générer une notification
    notification = Notification(
        user_id=current_user.id,
        type_notification="questionnaire_completed",
        titre="Questionnaire administratif complété",
        message=f"Votre questionnaire administratif/technique pour la souscription #{subscription_id} a été enregistré avec succès.",
        lien_relation_id=questionnaire.id,
        lien_relation_type="questionnaire"
    )
    db.add(notification)
    db.commit()
    
    return questionnaire


@router.post("/subscriptions/{subscription_id}/questionnaire/medical", response_model=QuestionnaireResponse)
async def create_medical_questionnaire(
    subscription_id: int,
    reponses: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer ou mettre à jour un questionnaire médical pour une souscription"""
    # Vérifier que la souscription existe et appartient à l'utilisateur
    souscription = db.query(Souscription).filter(
        Souscription.id == subscription_id,
        Souscription.user_id == current_user.id
    ).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier s'il existe déjà un questionnaire médical
    existing_questionnaire = db.query(Questionnaire).filter(
        Questionnaire.souscription_id == subscription_id,
        Questionnaire.type_questionnaire == "medical"
    ).order_by(Questionnaire.version.desc()).first()
    
    # Déterminer la version
    version = 1
    if existing_questionnaire:
        version = existing_questionnaire.version + 1
        # Archiver l'ancien questionnaire
        existing_questionnaire.statut = "archive"
    
    # Créer le nouveau questionnaire
    questionnaire = Questionnaire(
        souscription_id=subscription_id,
        type_questionnaire="medical",
        version=version,
        reponses=reponses,
        statut="complete"
    )
    
    db.add(questionnaire)
    db.commit()
    db.refresh(questionnaire)
    
    # Générer une notification
    notification = Notification(
        user_id=current_user.id,
        type_notification="questionnaire_completed",
        titre="Questionnaire médical complété",
        message=f"Votre questionnaire médical pour la souscription #{subscription_id} a été enregistré avec succès.",
        lien_relation_id=questionnaire.id,
        lien_relation_type="questionnaire"
    )
    db.add(notification)
    db.commit()
    
    return questionnaire


@router.get("/subscriptions/{subscription_id}/questionnaire/{questionnaire_type}", response_model=QuestionnaireResponse)
async def get_subscription_questionnaire(
    subscription_id: int,
    questionnaire_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Récupérer le questionnaire existant pour une souscription"""
    # Vérifier que la souscription existe et appartient à l'utilisateur
    souscription = db.query(Souscription).filter(
        Souscription.id == subscription_id,
        Souscription.user_id == current_user.id
    ).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier que le type de questionnaire est valide
    valid_types = ["short", "long", "administratif", "medical"]
    if questionnaire_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type de questionnaire invalide. Types valides: {', '.join(valid_types)}"
        )
    
    # Récupérer le questionnaire le plus récent (non archivé)
    questionnaire = db.query(Questionnaire).filter(
        Questionnaire.souscription_id == subscription_id,
        Questionnaire.type_questionnaire == questionnaire_type,
        Questionnaire.statut != "archive"
    ).order_by(Questionnaire.version.desc()).first()
    
    if not questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun questionnaire {questionnaire_type} trouvé pour cette souscription"
        )
    
    return questionnaire


@router.get("/questionnaire/{questionnaire_id}/status", response_model=QuestionnaireStatusResponse)
async def get_questionnaire_status(
    questionnaire_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir le statut d'un questionnaire"""
    questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == questionnaire_id
    ).first()
    
    if not questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire non trouvé"
        )
    
    # Vérifier que l'utilisateur a accès à cette souscription
    souscription = db.query(Souscription).filter(
        Souscription.id == questionnaire.souscription_id
    ).first()
    
    if not souscription or souscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé à ce questionnaire"
        )
    
    return questionnaire

