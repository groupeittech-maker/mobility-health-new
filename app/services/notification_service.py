"""
Service centralisé pour la gestion des notifications
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.core.database import SessionLocal
from app.models.notification import Notification
from app.models.user import User
from app.workers.tasks import (
    send_email,
    send_sms,
    send_push,
    send_notification_multi_channel
)
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service pour gérer les notifications"""
    
    @staticmethod
    def create_notification(
        user_id: int,
        type_notification: str,
        titre: str,
        message: str,
        lien_relation_id: Optional[int] = None,
        lien_relation_type: Optional[str] = None,
        send_immediately: bool = True,
        channels: Optional[List[str]] = None
    ) -> Notification:
        """
        Créer une notification et l'envoyer si demandé.
        
        Args:
            user_id: ID de l'utilisateur
            type_notification: Type de notification
            titre: Titre de la notification
            message: Message de la notification
            lien_relation_id: ID de l'entité liée
            lien_relation_type: Type de l'entité liée
            send_immediately: Envoyer immédiatement via Celery
            channels: Canaux d'envoi (email, sms, push)
        
        Returns:
            Notification créée
        """
        db = SessionLocal()
        try:
            notification = Notification(
                user_id=user_id,
                type_notification=type_notification,
                titre=titre,
                message=message,
                lien_relation_id=lien_relation_id,
                lien_relation_type=lien_relation_type
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # Envoyer immédiatement si demandé
            if send_immediately:
                if channels is None:
                    channels = ["email", "push"]  # Par défaut
                
                try:
                    send_notification_multi_channel.delay(
                        user_id=user_id,
                        notification_id=notification.id,
                        channels=channels
                    )
                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")
                    # On continue quand même, la notification est créée
            
            return notification
        finally:
            db.close()
    
    @staticmethod
    def send_questionnaire_completion_notification(
        user_id: int,
        subscription_id: int,
        questionnaire_id: int,
        questionnaire_type: str
    ) -> Notification:
        """Envoyer une notification de complétion de questionnaire"""
        return NotificationService.create_notification(
            user_id=user_id,
            type_notification="questionnaire_completed",
            titre=f"Questionnaire {questionnaire_type} complété",
            message=f"Votre questionnaire {questionnaire_type} pour la souscription #{subscription_id} a été enregistré avec succès.",
            lien_relation_id=questionnaire_id,
            lien_relation_type="questionnaire",
            channels=["email", "push"]
        )
    
    @staticmethod
    def send_sos_alert_notification(
        user_id: int,
        alert_id: int,
        location: Optional[str] = None
    ) -> Notification:
        """Envoyer une alerte SOS"""
        message = f"Alerte SOS activée"
        if location:
            message += f" à {location}"
        
        return NotificationService.create_notification(
            user_id=user_id,
            type_notification="sos_alert",
            titre="Alerte SOS",
            message=message,
            lien_relation_id=alert_id,
            lien_relation_type="sos",
            channels=["email", "sms", "push"]  # Tous les canaux pour une alerte SOS
        )
    
    @staticmethod
    def send_payment_confirmation_notification(
        user_id: int,
        payment_id: int,
        amount: float
    ) -> Notification:
        """Envoyer une notification de confirmation de paiement"""
        return NotificationService.create_notification(
            user_id=user_id,
            type_notification="payment_confirmed",
            titre="Paiement confirmé",
            message=f"Votre paiement de {amount}€ a été confirmé avec succès.",
            lien_relation_id=payment_id,
            lien_relation_type="payment",
            channels=["email", "push"]
        )
    
    @staticmethod
    def send_subscription_created_notification(
        user_id: int,
        subscription_id: int
    ) -> Notification:
        """Envoyer une notification de création de souscription"""
        return NotificationService.create_notification(
            user_id=user_id,
            type_notification="subscription_created",
            titre="Nouvelle souscription créée",
            message=f"Votre souscription #{subscription_id} a été créée avec succès.",
            lien_relation_id=subscription_id,
            lien_relation_type="subscription",
            channels=["email", "push"]
        )

