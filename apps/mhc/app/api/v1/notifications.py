from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.models.sinistre import Sinistre
from app.models.questionnaire import Questionnaire
from app.models.souscription import Souscription
from app.core.enums import Role
from app.core.referent_notifications import REFERENT_NOTIFICATION_TYPES
from pydantic import BaseModel

router = APIRouter()


def _check_and_create_long_questionnaire_reminder(db: Session, user_id: int):
    """Vérifier si l'utilisateur doit être notifié pour remplir le questionnaire long"""
    # Trouver tous les questionnaires courts complétés il y a au moins 3 jours
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    
    short_questionnaires = db.query(Questionnaire).filter(
        Questionnaire.type_questionnaire == "short",
        Questionnaire.statut == "complete",
        Questionnaire.created_at <= three_days_ago
    ).all()
    
    for short_q in short_questionnaires:
        # Vérifier que la souscription appartient à l'utilisateur
        souscription = db.query(Souscription).filter(
            Souscription.id == short_q.souscription_id,
            Souscription.user_id == user_id
        ).first()
        
        if not souscription:
            continue
        
        # Vérifier s'il existe déjà un questionnaire long pour cette souscription
        long_questionnaire = db.query(Questionnaire).filter(
            Questionnaire.souscription_id == short_q.souscription_id,
            Questionnaire.type_questionnaire == "long",
            Questionnaire.statut == "complete"
        ).first()
        
        if long_questionnaire:
            continue
        
        # Vérifier s'il existe déjà une notification non lue pour cette souscription
        existing_notification = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.type_notification == "questionnaire_long_reminder",
            Notification.lien_relation_id == short_q.souscription_id,
            Notification.lien_relation_type == "souscription",
            Notification.is_read == False  # noqa: E712
        ).first()
        
        if existing_notification:
            continue
        
        # Créer la notification
        notification = Notification(
            user_id=user_id,
            type_notification="questionnaire_long_reminder",
            titre="Questionnaire complet à remplir",
            message=f"📋 Informations:\n• Vous avez rempli le questionnaire court pour la souscription #{souscription.numero_souscription} il y a plus de 3 jours.\n• Pour compléter votre dossier, veuillez remplir le questionnaire complet (long).\n• Cliquez sur cette notification pour accéder au formulaire.",
            lien_relation_id=short_q.souscription_id,
            lien_relation_type="souscription"
        )
        db.add(notification)
    
    db.commit()


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type_notification: str
    titre: str
    message: str
    is_read: bool
    lien_relation_id: int | None
    lien_relation_type: str | None
    created_at: datetime
    # Renseigné quand lien_relation_type == sinistre (navigation app mobile → /sos/{alerte_id})
    alerte_id: int | None = None

    class Config:
        from_attributes = True


def _notification_to_response(db: Session, n: Notification) -> NotificationResponse:
    alerte_id = None
    if (n.lien_relation_type or "").lower() == "sinistre" and n.lien_relation_id:
        sinistre = (
            db.query(Sinistre).filter(Sinistre.id == n.lien_relation_id).first()
        )
        if sinistre is not None:
            alerte_id = sinistre.alerte_id
    return NotificationResponse(
        id=n.id,
        user_id=n.user_id,
        type_notification=n.type_notification,
        titre=n.titre,
        message=n.message,
        is_read=n.is_read,
        lien_relation_id=n.lien_relation_id,
        lien_relation_type=n.lien_relation_type,
        created_at=n.created_at,
        alerte_id=alerte_id,
    )


async def _get_notifications_handler(
    skip: int = 0,
    limit: int = 100,
    type_notification: Optional[str] = None,
    is_read: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user notifications
    
    Args:
        skip: Nombre de notifications à ignorer (pagination)
        limit: Nombre maximum de notifications à retourner
        type_notification: Filtrer par type de notification (optionnel)
        is_read: Filtrer par statut de lecture (True/False, optionnel)
    """
    # Réservé aux comptes assuré (pas médecin référent / staff)
    if current_user.role == Role.USER:
        _check_and_create_long_questionnaire_reminder(db, current_user.id)
    
    # Pour les opérateurs SOS, ils peuvent voir toutes les notifications liées aux alertes SOS
    # et aux factures, pas seulement les leurs
    sos_notification_types = ["sos_alert_received", "invoice_received", "sos_alert_hospital"]
    
    if current_user.role == Role.SOS_OPERATOR or current_user.role == Role.AGENT_SINISTRE_MH:
        # Les opérateurs SOS voient leurs propres notifications ET les notifications SOS
        query = db.query(Notification).filter(
            or_(
                Notification.user_id == current_user.id,
                Notification.type_notification.in_(sos_notification_types)
            )
        )
    else:
        # Les autres utilisateurs ne voient que leurs propres notifications
        query = db.query(Notification).filter(
            Notification.user_id == current_user.id
        )
        # Médecin référent MH : uniquement SOS / rapport / facture (pas questionnaires assuré, etc.)
        if current_user.role == Role.MEDECIN_REFERENT_MH:
            query = query.filter(
                Notification.type_notification.in_(list(REFERENT_NOTIFICATION_TYPES))
            )

    # Appliquer les filtres optionnels
    if type_notification:
        query = query.filter(Notification.type_notification == type_notification)
    
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return [_notification_to_response(db, n) for n in notifications]


# Route avec trailing slash (pour compatibilité)
@router.get("/", response_model=List[NotificationResponse])
async def get_notifications_with_slash(
    skip: int = 0,
    limit: int = 100,
    type_notification: Optional[str] = None,
    is_read: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user notifications (with trailing slash)"""
    return await _get_notifications_handler(skip, limit, type_notification, is_read, db, current_user)


# Note: La route sans trailing slash est ajoutée dans __init__.py via add_api_route


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notification by ID"""
    sos_notification_types = ["sos_alert_received", "invoice_received", "sos_alert_hospital"]
    
    # Pour les opérateurs SOS, ils peuvent accéder aux notifications SOS même si elles ne leur appartiennent pas
    if current_user.role == Role.SOS_OPERATOR or current_user.role == Role.AGENT_SINISTRE_MH:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            or_(
                Notification.user_id == current_user.id,
                Notification.type_notification.in_(sos_notification_types)
            )
        ).first()
    else:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )

    return _notification_to_response(db, notification)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marquer une notification comme lue"""
    sos_notification_types = ["sos_alert_received", "invoice_received", "sos_alert_hospital"]
    
    # Pour les opérateurs SOS, ils peuvent marquer comme lues les notifications SOS même si elles ne leur appartiennent pas
    if current_user.role == Role.SOS_OPERATOR or current_user.role == Role.AGENT_SINISTRE_MH:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            or_(
                Notification.user_id == current_user.id,
                Notification.type_notification.in_(sos_notification_types)
            )
        ).first()
    else:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    notification.is_read = True
    db.commit()
    db.refresh(notification)

    return _notification_to_response(db, notification)

