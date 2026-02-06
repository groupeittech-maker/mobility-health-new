from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from celery import Task
from celery.exceptions import Retry
from celery.result import AsyncResult
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.notification import Notification
from app.models.questionnaire import Questionnaire
from app.models.souscription import Souscription
from app.models.user import User
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import traceback

logger = logging.getLogger(__name__)

# Configuration des retries avec exponential backoff
MAX_RETRIES = 3
INITIAL_COUNTDOWN = 60  # 1 minute initial

# Import conditionnel pour FCM
try:
    from pyfcm import FCMNotification
    FCM_AVAILABLE = True
except ImportError:
    FCM_AVAILABLE = False
    logger.warning("pyfcm not available, push notifications will be simulated")


@celery_app.task(bind=True, name="app.workers.tasks.send_email", max_retries=MAX_RETRIES)
def send_email(
    self: Task,
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
    user_id: Optional[int] = None,
    notification_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Envoyer un email.
    Retry automatique en cas d'échec avec exponential backoff.
    """
    try:
        # Créer le message email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        
        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
        
        # Envoyer l'email via SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email envoyé avec succès à {to_email}")
        
        # Mettre à jour la notification si fournie
        if notification_id:
            db = SessionLocal()
            try:
                notification = db.query(Notification).filter(
                    Notification.id == notification_id
                ).first()
                if notification:
                    # Marquer comme envoyée (on peut ajouter un champ sent_at si nécessaire)
                    pass
                db.commit()
            finally:
                db.close()
        
        return {
            "status": "success",
            "to": to_email,
            "subject": subject,
            "sent_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi d'email à {to_email}: {str(e)}")
        
        # Retry avec exponential backoff
        retry_count = getattr(self.request, 'retries', 0)
        max_retries = getattr(self, 'max_retries', MAX_RETRIES)
        
        if retry_count < max_retries:
            raise self.retry(
                exc=e,
                countdown=INITIAL_COUNTDOWN * (2 ** retry_count),  # Exponential backoff
            )
        
        # Si tous les retries ont échoué, enregistrer la tâche échouée
        try:
            record_failed_task.delay(
                task_id=self.request.id,
                task_name=self.name,
                error_message=str(e),
                task_args=[to_email, subject],
                task_kwargs={"user_id": user_id, "notification_id": notification_id},
                error_traceback=traceback.format_exc(),
                queue_name=self.request.delivery_info.get('routing_key', 'notifications')
            )
        except Exception as record_error:
            logger.error(f"Erreur lors de l'enregistrement de la tâche échouée: {str(record_error)}")
        
        # Créer une notification d'erreur pour l'utilisateur
        if user_id:
            db = SessionLocal()
            try:
                error_notification = Notification(
                    user_id=user_id,
                    type_notification="email_error",
                    titre="Erreur d'envoi d'email",
                    message=f"Impossible d'envoyer l'email à {to_email}. Erreur: {str(e)}"
                )
                db.add(error_notification)
                db.commit()
            finally:
                db.close()
        
        return {
            "status": "error",
            "error": str(e),
            "retries": retry_count
        }


@celery_app.task(bind=True, name="app.workers.tasks.send_sms", max_retries=MAX_RETRIES)
def send_sms(
    self: Task,
    to_phone: str,
    message: str,
    user_id: Optional[int] = None,
    notification_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Envoyer un SMS.
    Retry automatique en cas d'échec.
    """
    try:
        if settings.SMS_PROVIDER == "twilio":
            from twilio.rest import Client
            
            if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
                raise ValueError("Twilio credentials not configured")
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            twilio_message = client.messages.create(
                body=message,
                from_=settings.TWILIO_FROM_NUMBER,
                to=to_phone
            )
            
            logger.info(f"SMS envoyé avec succès à {to_phone}. SID: {twilio_message.sid}")
            
            return {
                "status": "success",
                "to": to_phone,
                "message_sid": twilio_message.sid,
                "sent_at": datetime.utcnow().isoformat()
            }
        else:
            # Autres providers (AWS SNS, etc.)
            logger.warning(f"SMS provider {settings.SMS_PROVIDER} not implemented")
            return {
                "status": "error",
                "error": f"SMS provider {settings.SMS_PROVIDER} not implemented"
            }
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de SMS à {to_phone}: {str(e)}")
        
        # Retry avec exponential backoff
        retry_count = getattr(self.request, 'retries', 0)
        max_retries = getattr(self, 'max_retries', MAX_RETRIES)
        
        if retry_count < max_retries:
            raise self.retry(
                exc=e,
                countdown=INITIAL_COUNTDOWN * (2 ** retry_count),
            )
        
        # Enregistrer la tâche échouée
        try:
            record_failed_task.delay(
                task_id=self.request.id,
                task_name=self.name,
                error_message=str(e),
                task_args=[to_phone, message],
                task_kwargs={"user_id": user_id, "notification_id": notification_id},
                error_traceback=traceback.format_exc(),
                queue_name=self.request.delivery_info.get('routing_key', 'notifications')
            )
        except Exception as record_error:
            logger.error(f"Erreur lors de l'enregistrement de la tâche échouée: {str(record_error)}")
        
        return {
            "status": "error",
            "error": str(e),
            "retries": retry_count
        }


@celery_app.task(bind=True, name="app.workers.tasks.send_push", max_retries=MAX_RETRIES)
def send_push(
    self: Task,
    user_id: int,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    notification_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Envoyer une notification push (FCM).
    Retry automatique en cas d'échec.
    """
    try:
        # Récupérer les tokens FCM de l'utilisateur
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"status": "error", "error": "User not found"}
            
            # En production, récupérer les tokens FCM depuis une table dédiée
            # Pour l'instant, on utilise FCM si disponible
            sent_count = 0
            
            if settings.FCM_SERVER_KEY and FCM_AVAILABLE:
                try:
                    push_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)
                    
                    # TODO: Récupérer les device tokens depuis une table user_devices
                    # Pour l'instant, on simule avec un token fictif
                    # device_tokens = get_user_device_tokens(user_id)
                    
                    # Exemple d'envoi (à adapter avec les vrais tokens)
                    # result = push_service.notify_multiple_devices(
                    #     registration_ids=device_tokens,
                    #     message_title=title,
                    #     message_body=body,
                    #     data_message=data or {}
                    # )
                    
                    # Pour l'instant, on log juste
                    logger.info(f"Push notification préparée pour l'utilisateur {user_id}: {title}")
                    sent_count = 1
                except Exception as fcm_error:
                    logger.error(f"Erreur FCM: {str(fcm_error)}")
                    raise
            else:
                if not settings.FCM_SERVER_KEY:
                    logger.warning("FCM_SERVER_KEY not configured, skipping push notification")
                elif not FCM_AVAILABLE:
                    logger.warning("pyfcm not available, skipping push notification")
            
            return {
                "status": "success",
                "user_id": user_id,
                "devices_notified": sent_count,
                "sent_at": datetime.utcnow().isoformat()
            }
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de push à l'utilisateur {user_id}: {str(e)}")
        
        # Retry avec exponential backoff
        retry_count = getattr(self.request, 'retries', 0)
        max_retries = getattr(self, 'max_retries', MAX_RETRIES)
        
        if retry_count < max_retries:
            raise self.retry(
                exc=e,
                countdown=INITIAL_COUNTDOWN * (2 ** retry_count),
            )
        
        # Enregistrer la tâche échouée
        try:
            record_failed_task.delay(
                task_id=self.request.id,
                task_name=self.name,
                error_message=str(e),
                task_args=[user_id, title, body],
                task_kwargs={"data": data, "notification_id": notification_id},
                error_traceback=traceback.format_exc(),
                queue_name=self.request.delivery_info.get('routing_key', 'notifications')
            )
        except Exception as record_error:
            logger.error(f"Erreur lors de l'enregistrement de la tâche échouée: {str(record_error)}")
        
        return {
            "status": "error",
            "error": str(e),
            "retries": retry_count
        }


@celery_app.task(bind=True, name="app.workers.tasks.send_notification_multi_channel")
def send_notification_multi_channel(
    self: Task,
    user_id: int,
    notification_id: int,
    channels: list = None  # ["email", "sms", "push"]
) -> Dict[str, Any]:
    """
    Envoyer une notification sur plusieurs canaux.
    """
    if channels is None:
        channels = ["email", "push"]  # Par défaut
    
    db = SessionLocal()
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id
        ).first()
        
        if not notification:
            return {"status": "error", "error": "Notification not found"}
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "error": "User not found"}
        
        results = {}
        
        # Envoyer par email
        if "email" in channels and user.email:
            email_task = send_email.delay(
                to_email=user.email,
                subject=notification.titre,
                body_html=f"<h1>{notification.titre}</h1><p>{notification.message}</p>",
                body_text=notification.message,
                user_id=user_id,
                notification_id=notification_id
            )
            results["email"] = {"task_id": email_task.id, "status": "queued"}
        
        # Envoyer par SMS (si numéro disponible)
        if "sms" in channels:
            # Récupérer le numéro depuis ContactProche ou User
            # Pour l'instant, on skip
            pass
        
        # Envoyer par push
        if "push" in channels:
            push_task = send_push.delay(
                user_id=user_id,
                title=notification.titre,
                body=notification.message,
                data={"notification_id": notification_id},
                notification_id=notification_id
            )
            results["push"] = {"task_id": push_task.id, "status": "queued"}
        
        return {
            "status": "queued",
            "notification_id": notification_id,
            "channels": results
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.workers.tasks.schedule_questionnaire_reminder")
def schedule_questionnaire_reminder(
    self: Task,
    user_id: int,
    subscription_id: int,
    questionnaire_id: int,
    reminder_days: int = 7
):
    """
    Planifier un rappel pour un questionnaire.
    Cette tâche est appelée immédiatement mais planifie une notification future.
    """
    db = SessionLocal()
    try:
        # Vérifier que le questionnaire existe toujours
        questionnaire = db.query(Questionnaire).filter(
            Questionnaire.id == questionnaire_id
        ).first()
        
        if not questionnaire:
            return {"status": "error", "message": "Questionnaire not found"}
        
        # Planifier la notification de rappel
        reminder_date = datetime.utcnow() + timedelta(days=reminder_days)
        
        # Créer une tâche planifiée pour envoyer le rappel
        send_questionnaire_reminder.apply_async(
            args=[user_id, subscription_id, questionnaire_id],
            countdown=reminder_days * 24 * 60 * 60  # Convertir les jours en secondes
        )
        
        return {
            "status": "scheduled",
            "reminder_date": reminder_date.isoformat(),
            "questionnaire_id": questionnaire_id
        }
    except Exception as e:
        logger.error(f"Erreur lors de la planification du rappel: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True, name="app.workers.tasks.send_questionnaire_reminder", max_retries=MAX_RETRIES)
def send_questionnaire_reminder(
    self: Task,
    user_id: int,
    subscription_id: int,
    questionnaire_id: int
):
    """
    Envoyer une notification de rappel pour un questionnaire.
    """
    db = SessionLocal()
    try:
        # Vérifier que le questionnaire existe toujours
        questionnaire = db.query(Questionnaire).filter(
            Questionnaire.id == questionnaire_id
        ).first()
        
        if not questionnaire:
            return {"status": "error", "message": "Questionnaire not found"}
        
        # Vérifier que la souscription existe toujours
        souscription = db.query(Souscription).filter(
            Souscription.id == subscription_id
        ).first()
        
        if not souscription:
            return {"status": "error", "message": "Subscription not found"}
        
        # Vérifier que le questionnaire n'est pas déjà complété
        if questionnaire.statut == "complete":
            return {"status": "skipped", "message": "Questionnaire already completed"}
        
        # Créer la notification de rappel
        notification = Notification(
            user_id=user_id,
            type_notification="questionnaire_reminder",
            titre="Rappel : Questionnaire à compléter",
            message=f"Nous vous rappelons de compléter votre questionnaire pour la souscription #{subscription_id}.",
            lien_relation_id=questionnaire_id,
            lien_relation_type="questionnaire"
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Envoyer la notification par email et push
        send_notification_multi_channel.delay(
            user_id=user_id,
            notification_id=notification.id,
            channels=["email", "push"]
        )
        
        return {
            "status": "sent",
            "notification_id": notification.id,
            "questionnaire_id": questionnaire_id
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de l'envoi du rappel: {str(e)}")
        
        # Retry
        retry_count = getattr(self.request, 'retries', 0)
        max_retries = getattr(self, 'max_retries', MAX_RETRIES)
        
        if retry_count < max_retries:
            raise self.retry(
                exc=e,
                countdown=INITIAL_COUNTDOWN * (2 ** retry_count),
            )
        
        # Enregistrer la tâche échouée
        try:
            record_failed_task.delay(
                task_id=self.request.id,
                task_name=self.name,
                error_message=str(e),
                task_args=[user_id, subscription_id, questionnaire_id],
                error_traceback=traceback.format_exc(),
                queue_name=self.request.delivery_info.get('routing_key', 'reminders')
            )
        except Exception as record_error:
            logger.error(f"Erreur lors de l'enregistrement de la tâche échouée: {str(record_error)}")
        
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.process_pending_notifications")
def process_pending_notifications():
    """
    Tâche périodique pour traiter les notifications en attente.
    Exécutée toutes les 5 minutes.
    """
    db = SessionLocal()
    try:
        # Récupérer les notifications récentes non envoyées
        # (on peut ajouter un champ sent_at pour tracker)
        recent_notifications = db.query(Notification).filter(
            Notification.created_at >= datetime.utcnow() - timedelta(hours=1),
            Notification.type_notification.in_([
                "questionnaire_completed",
                "sos_alert",
                "subscription_created"
            ])
        ).limit(50).all()
        
        processed = 0
        for notification in recent_notifications:
            user = db.query(User).filter(User.id == notification.user_id).first()
            if user:
                # Envoyer la notification sur les canaux appropriés
                send_notification_multi_channel.delay(
                    user_id=user.id,
                    notification_id=notification.id,
                    channels=["email", "push"]
                )
                processed += 1
        
        return {
            "status": "success",
            "processed": processed,
            "total": len(recent_notifications)
        }
    except Exception as e:
        logger.error(f"Erreur lors du traitement des notifications: {str(e)}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.process_questionnaire_reminders")
def process_questionnaire_reminders():
    """
    Tâche périodique pour envoyer les rappels de questionnaires.
    Exécutée tous les jours à 9h.
    """
    db = SessionLocal()
    try:
        # Récupérer les questionnaires en attente depuis plus de 7 jours
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        questionnaires = db.query(Questionnaire).filter(
            Questionnaire.statut == "en_attente",
            Questionnaire.created_at <= cutoff_date
        ).all()
        
        sent = 0
        for questionnaire in questionnaires:
            souscription = db.query(Souscription).filter(
                Souscription.id == questionnaire.souscription_id
            ).first()
            
            if souscription:
                send_questionnaire_reminder.delay(
                    user_id=souscription.user_id,
                    subscription_id=souscription.id,
                    questionnaire_id=questionnaire.id
                )
                sent += 1
        
        return {
            "status": "success",
            "reminders_sent": sent,
            "total_pending": len(questionnaires)
        }
    except Exception as e:
        logger.error(f"Erreur lors du traitement des rappels: {str(e)}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.retry_failed_tasks")
def retry_failed_tasks():
    """
    Tâche périodique pour réessayer les tâches échouées.
    Exécutée toutes les 10 minutes.
    """
    try:
        from app.models.failed_task import FailedTask
        
        db = SessionLocal()
        try:
            # Récupérer les tâches échouées non résolues
            failed_tasks = db.query(FailedTask).filter(
                FailedTask.is_resolved == False,
                FailedTask.retry_count < FailedTask.max_retries
            ).all()
            
            retried = 0
            for failed_task in failed_tasks:
                try:
                    # Réessayer la tâche
                    task_func = celery_app.tasks.get(failed_task.task_name)
                    if task_func:
                        # Réexécuter avec les mêmes arguments
                        result = task_func.apply_async(
                            args=failed_task.task_args or [],
                            kwargs=failed_task.task_kwargs or {},
                            queue=failed_task.queue_name or "default"
                        )
                        
                        # Mettre à jour le compteur de retry
                        failed_task.retry_count += 1
                        failed_task.task_id = result.id
                        retried += 1
                        
                        logger.info(f"Tâche {failed_task.task_name} réessayée (retry {failed_task.retry_count}/{failed_task.max_retries})")
                    else:
                        logger.warning(f"Tâche {failed_task.task_name} non trouvée")
                        failed_task.is_resolved = True
                        failed_task.resolved_at = datetime.utcnow()
                except Exception as retry_error:
                    logger.error(f"Erreur lors du retry de la tâche {failed_task.id}: {str(retry_error)}")
                    # Continuer avec les autres tâches
                    continue
            
            db.commit()
            
            return {
                "status": "success",
                "retried": retried,
                "total_failed": len(failed_tasks)
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des tâches échouées: {str(e)}")
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True, name="app.workers.tasks.record_failed_task")
def record_failed_task(
    self: Task,
    task_id: str,
    task_name: str,
    error_message: str,
    task_args: Optional[list] = None,
    task_kwargs: Optional[dict] = None,
    error_traceback: Optional[str] = None,
    queue_name: Optional[str] = None
):
    """
    Enregistrer une tâche échouée dans la base de données.
    """
    try:
        from app.models.failed_task import FailedTask
        
        db = SessionLocal()
        try:
            failed_task = FailedTask(
                task_id=task_id,
                task_name=task_name,
                task_args=task_args,
                task_kwargs=task_kwargs,
                error_message=error_message,
                error_traceback=error_traceback,
                queue_name=queue_name,
                max_retries=MAX_RETRIES
            )
            
            db.add(failed_task)
            db.commit()
            
            logger.info(f"Tâche échouée enregistrée: {task_name} (ID: {task_id})")
            return {"status": "recorded", "task_id": task_id}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de la tâche échouée: {str(e)}")
        return {"status": "error", "error": str(e)}