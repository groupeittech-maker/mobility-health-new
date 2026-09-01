"""
Envoi des notifications FCM via l'API HTTP v1 (compte de service).

Google ne fournit plus l'ancienne « clé serveur » sur les projets récents :
téléchargez un JSON « compte de service » (Firebase Console → Paramètres du projet
→ Comptes de service → Générer une nouvelle clé privée) et pointez
FCM_SERVICE_ACCOUNT_PATH vers ce fichier, ou définissez GOOGLE_APPLICATION_CREDENTIALS.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_firebase_ready: bool = False


def fcm_v1_configured() -> bool:
    """True si un fichier JSON de compte de service est disponible (sans initialiser Firebase)."""
    from app.core.config import settings

    if (getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "") or "").strip():
        return True
    path = (getattr(settings, "FCM_SERVICE_ACCOUNT_PATH", "") or "").strip()
    if path and os.path.isfile(path):
        return True
    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "") or ""
    return bool(gac and os.path.isfile(gac))


def _ensure_firebase_app() -> bool:
    global _firebase_ready
    if _firebase_ready:
        return True

    from firebase_admin import credentials, initialize_app, get_app
    from app.core.config import settings

    try:
        get_app()
        _firebase_ready = True
        return True
    except ValueError:
        pass

    cred_obj = None
    raw_json = (getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "") or "").strip()
    if raw_json:
        try:
            cred_obj = credentials.Certificate(json.loads(raw_json))
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error("FCM_SERVICE_ACCOUNT_JSON invalide: %s", e)
            return False
    else:
        path = (getattr(settings, "FCM_SERVICE_ACCOUNT_PATH", "") or "").strip()
        if not path:
            path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "") or ""
        if not path or not os.path.isfile(path):
            return False
        cred_obj = credentials.Certificate(path)

    try:
        initialize_app(cred_obj)
    except ValueError as e:
        if "already exists" in str(e).lower():
            _firebase_ready = True
            return True
        logger.error("Firebase initialize_app: %s", e)
        return False
    except Exception as e:
        logger.error("Firebase initialize_app: %s", e)
        return False

    _firebase_ready = True
    return True


def send_push_fcm_v1(
    registration_token: str,
    title: str,
    body: str,
    data: Dict[str, str],
    *,
    android_channel_id: str = "mh_referent",
    apns_badge: Optional[int] = None,
    android_notification_count: Optional[int] = None,
) -> Tuple[bool, Optional[str], Any]:
    """
    Envoie une notification FCM HTTP v1.
    Retourne (succès, code_erreur_basé_sur_exception, message_id_ou_détail).
    """
    from firebase_admin import messaging

    if not _ensure_firebase_app():
        return False, "firebase_init_failed", None

    safe_title = (title or "")[:200]
    safe_body = (body or "")[:3500]

    android_notif_kwargs: Dict[str, Any] = {
        "channel_id": android_channel_id,
        "sound": "default",
    }
    if android_notification_count is not None and android_notification_count > 0:
        android_notif_kwargs["notification_count"] = android_notification_count

    android_cfg = messaging.AndroidConfig(
        notification=messaging.AndroidNotification(**android_notif_kwargs),
    )

    apns_cfg = None
    if apns_badge is not None:
        apns_cfg = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound="default",
                    badge=apns_badge,
                ),
            ),
        )

    message = messaging.Message(
        notification=messaging.Notification(title=safe_title, body=safe_body),
        data=data or None,
        android=android_cfg,
        apns=apns_cfg,
        token=registration_token,
    )

    try:
        msg_id = messaging.send(message)
        return True, None, msg_id
    except messaging.UnregisteredError as e:
        return False, "unregistered", str(e)
    except messaging.SenderIdMismatchError as e:
        return False, "sender_mismatch", str(e)
    except Exception as e:
        err = str(e).lower()
        return False, err, str(e)


def should_clear_fcm_token_after_error(error_hint: Optional[str], detail: Any) -> bool:
    """True si le jeton d'appareil doit être retiré de la base."""
    blob = f"{error_hint or ''} {detail or ''}".lower()
    return any(
        x in blob
        for x in (
            "unregistered",
            "registration-token-not-registered",
            "requested entity was not found",
            "not a valid fcm registration token",
        )
    )
