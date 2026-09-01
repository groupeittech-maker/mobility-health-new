from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from celery import Task
from celery.exceptions import Retry
from celery.result import AsyncResult
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.referent_notifications import REFERENT_NOTIFICATION_TYPES
from app.models.notification import Notification
from app.models.sinistre import Sinistre
from app.models.questionnaire import Questionnaire
from app.models.souscription import Souscription
from app.models.user import User
from app.core.enums import Role
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import traceback

logger = logging.getLogger(__name__)

# Alias historique (push FCM référent = mêmes types que la liste in-app)
REFERENT_FCM_TYPES = REFERENT_NOTIFICATION_TYPES


def _user_role_str(user: User) -> str:
    r = user.role
    return (r.value if hasattr(r, "value") else str(r)).lower().strip()


def _referent_unread_badge_count(db, user_id: int) -> int:
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
            Notification.type_notification.in_(list(REFERENT_FCM_TYPES)),
        )
        .count()
    )


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
        
        # Envoyer l'email via SMTP en supportant STARTTLS et SSL direct (ex: Hostinger 465)
        smtp_security = str(getattr(settings, "SMTP_SECURITY", "starttls") or "starttls").strip().lower()
        if smtp_security == "ssl":
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if smtp_security == "starttls":
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
    Envoyer une notification push (FCM) au jeton enregistré sur l'utilisateur (app mobile).
    """
    try:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"status": "error", "error": "User not found"}

            reg_id = (getattr(user, "fcm_registration_token", None) or "").strip()
            if not reg_id:
                logger.warning("Push ignoré: aucun jeton FCM pour user_id=%s", user_id)
                return {"status": "skipped", "reason": "no_fcm_token", "user_id": user_id}

            from app.services.fcm_push import (
                fcm_v1_configured,
                send_push_fcm_v1,
                should_clear_fcm_token_after_error,
            )

            notif_row = None
            if notification_id:
                notif_row = (
                    db.query(Notification)
                    .filter(Notification.id == notification_id)
                    .first()
                )

            role_s = _user_role_str(user)
            ntype = (
                (notif_row.type_notification if notif_row else None)
                or (data or {}).get("type_notification")
            )
            if role_s == Role.MEDECIN_REFERENT_MH.value:
                if not ntype or str(ntype) not in REFERENT_FCM_TYPES:
                    logger.info(
                        "Push FCM non envoyée au médecin référent (type non concerné): %s",
                        ntype,
                    )
                    return {
                        "status": "skipped",
                        "reason": "referent_only_sos_report_invoice",
                        "user_id": user_id,
                    }

            safe_title = (title or "")[:200]
            safe_body = (body or "")[:3500]
            data_payload: Dict[str, str] = {}
            if data:
                for k, v in data.items():
                    if v is not None:
                        data_payload[str(k)] = str(v)[:1024]
            if notif_row:
                data_payload.setdefault("notification_id", str(notification_id))
                data_payload["type_notification"] = str(notif_row.type_notification)
                if notif_row.lien_relation_id is not None:
                    data_payload.setdefault(
                        "lien_relation_id", str(notif_row.lien_relation_id)
                    )
                if notif_row.lien_relation_type:
                    data_payload.setdefault(
                        "lien_relation_type", str(notif_row.lien_relation_type)
                    )
                lt = (notif_row.lien_relation_type or "").lower()
                lid = notif_row.lien_relation_id
                if lt == "sinistre" and lid:
                    sinistre = (
                        db.query(Sinistre).filter(Sinistre.id == lid).first()
                    )
                    if sinistre is not None and sinistre.alerte_id:
                        data_payload["alerte_id"] = str(sinistre.alerte_id)
                elif lt == "invoice" and lid:
                    data_payload.setdefault("invoice_id", str(lid))

            badge_n: Optional[int] = None
            if role_s == Role.MEDECIN_REFERENT_MH.value:
                badge_n = _referent_unread_badge_count(db, user_id)
                data_payload["mh_badge"] = str(badge_n)

            has_v1 = fcm_v1_configured()
            has_legacy = bool(settings.FCM_SERVER_KEY) and FCM_AVAILABLE

            if not has_v1 and not has_legacy:
                logger.warning(
                    "FCM non configuré : définissez FCM_SERVICE_ACCOUNT_PATH (HTTP v1) "
                    "ou FCM_SERVER_KEY + pyfcm (legacy)"
                )
                return {"status": "skipped", "reason": "fcm_not_configured", "user_id": user_id}

            if has_v1:
                ok, err_hint, detail = send_push_fcm_v1(
                    reg_id,
                    safe_title,
                    safe_body,
                    data_payload,
                    apns_badge=badge_n,
                    android_notification_count=badge_n,
                )
                if not ok:
                    if should_clear_fcm_token_after_error(err_hint, detail):
                        user.fcm_registration_token = None
                        db.commit()
                        logger.info("Jeton FCM supprimé pour user_id=%s", user_id)
                    logger.warning(
                        "FCM HTTP v1 échec user_id=%s notification_id=%s: %s",
                        user_id,
                        notification_id,
                        detail,
                    )
                    return {
                        "status": "error",
                        "user_id": user_id,
                        "error": detail or err_hint,
                        "sent_at": datetime.utcnow().isoformat(),
                    }
                logger.info(
                    "Push FCM HTTP v1 user_id=%s notification_id=%s msg=%s",
                    user_id,
                    notification_id,
                    detail,
                )
                return {
                    "status": "success",
                    "user_id": user_id,
                    "fcm_transport": "http_v1",
                    "fcm_result": str(detail),
                    "sent_at": datetime.utcnow().isoformat(),
                }

            push_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)
            badge_kw: Dict[str, Any] = {}
            if badge_n is not None:
                badge_kw["badge"] = badge_n

            result = push_service.notify_single_device(
                registration_id=reg_id,
                message_title=safe_title,
                message_body=safe_body,
                data_message=data_payload or None,
                sound="default",
                android_channel_id="mh_referent",
                **badge_kw,
            )

            failure = 0
            if isinstance(result, dict):
                failure = int(result.get("failure", 0) or 0)
            if failure > 0 and isinstance(result, dict):
                results = result.get("results")
                err_low = ""
                if isinstance(results, list) and results:
                    err_low = str((results[0] or {}).get("error", "")).lower()
                if "notregistered" in err_low or "invalidregistration" in err_low:
                    user.fcm_registration_token = None
                    db.commit()
                    logger.info("Jeton FCM invalide supprimé pour user_id=%s", user_id)

            logger.info(
                "Push FCM (legacy) user_id=%s notification_id=%s",
                user_id,
                notification_id,
            )
            return {
                "status": "success",
                "user_id": user_id,
                "fcm_transport": "legacy",
                "fcm_result": result,
                "sent_at": datetime.utcnow().isoformat(),
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
    Dispatcher Celery : push (et SMS si implémenté). L'e-mail n'est pas déclenché ici.
    """
    if channels is None:
        channels = ["push"]

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

        # Envoi e-mail désactivé pour les notifications file Celery (push / WebSocket côté API).

        # Envoyer par SMS (si numéro disponible)
        if "sms" in channels:
            # Récupérer le numéro depuis ContactProche ou User
            # Pour l'instant, on skip
            pass
        
        # Envoyer par push
        if "push" in channels:
            if (
                _user_role_str(user) == Role.MEDECIN_REFERENT_MH.value
                and notification.type_notification not in REFERENT_FCM_TYPES
            ):
                return {
                    "status": "skipped",
                    "reason": "referent_only_sos_report_invoice",
                    "notification_id": notification_id,
                    "type_notification": notification.type_notification,
                }
            push_task = send_push.delay(
                user_id=user_id,
                title=notification.titre,
                body=notification.message,
                data={
                    "notification_id": str(notification_id),
                    "type_notification": notification.type_notification,
                },
                notification_id=notification_id,
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
            channels=["push"]
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
    Ancienne file de « relance » push (toutes les 5 min) sans garde-fou : doublons et spam.
    Désactivée : l’envoi se fait à la création via send_notification_multi_channel.
    """
    logger.info("process_pending_notifications: désactivée (aucun renvoi périodique)")
    return {"status": "disabled", "processed": 0}


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