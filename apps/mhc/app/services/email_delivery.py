"""Envoi SMTP (synchrone) et dispatch vers Celery pour les e-mails MHC."""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Échec d'envoi SMTP (configuration ou serveur)."""


def smtp_configured() -> bool:
    return bool(
        (settings.SMTP_HOST or "").strip()
        and (settings.SMTP_USER or "").strip()
        and (settings.SMTP_PASSWORD or "").strip()
    )


def deliver_email_sync(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Envoie un e-mail immédiatement via SMTP."""
    if not smtp_configured():
        raise EmailDeliveryError(
            "Configuration SMTP incomplète (SMTP_HOST, SMTP_USER, SMTP_PASSWORD)."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    smtp_security = str(getattr(settings, "SMTP_SECURITY", "starttls") or "starttls").strip().lower()
    try:
        if smtp_security == "ssl":
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                if smtp_security == "starttls":
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
    except Exception as exc:
        logger.error("Échec envoi SMTP vers %s: %s", to_email, exc)
        raise EmailDeliveryError(str(exc)) from exc

    logger.info("E-mail envoyé (SMTP direct) à %s", to_email)
    return {"status": "success", "to": to_email, "subject": subject, "mode": "sync"}


def dispatch_email(
    *,
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
    user_id: Optional[int] = None,
    synchronous: bool = False,
) -> Dict[str, Any]:
    """
    Envoie un e-mail.
    - synchronous=True : SMTP immédiat (codes auth, vérification).
    - sinon : file Celery, avec repli SMTP si le broker est indisponible.
    """
    if synchronous:
        return deliver_email_sync(to_email, subject, body_html, body_text)

    from app.workers.tasks import send_email

    try:
        send_email.delay(
            to_email=to_email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            user_id=user_id,
        )
        return {"status": "queued", "to": to_email, "subject": subject, "mode": "celery"}
    except Exception as exc:
        logger.warning("Celery indisponible pour %s, envoi SMTP direct: %s", to_email, exc)
        return deliver_email_sync(to_email, subject, body_html, body_text)
