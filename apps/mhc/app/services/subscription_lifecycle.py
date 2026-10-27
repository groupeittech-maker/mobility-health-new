"""Cycle de vie des souscriptions (workflow MyMHC V3).

- Informations complémentaires demandées par MHC (§4.2) : notification immédiate,
  rappel avant l'échéance, refus automatique (motif + horodatage) sans réponse
  sous INFO_REQUEST_DELAY_HOURS. Aucun paiement n'ayant eu lieu, rien à rembourser.
- Fin de couverture (§5) : les polices actives dont la période est terminée
  passent en « Expirée » (carte retirée du carrousel actif).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import StatutSouscription
from app.models.souscription import Souscription

logger = logging.getLogger(__name__)

INFO_TIMEOUT_REASON = (
    "Refus automatique : informations complémentaires non transmises dans le délai de {hours} h."
)


def _notify(user_id: int, type_notification: str, titre: str, message: str, souscription_id: int) -> None:
    try:
        from app.services.notification_service import NotificationService

        NotificationService.create_notification(
            user_id=user_id,
            type_notification=type_notification,
            titre=titre,
            message=message,
            lien_relation_id=souscription_id,
            lien_relation_type="souscription",
            channels=["push"],
        )
    except Exception as exc:  # pragma: no cover - la notification ne bloque jamais le flux
        logger.warning("Notification %s impossible (souscription %s): %s", type_notification, souscription_id, exc)


def info_request_pending(souscription: Souscription) -> bool:
    return bool(souscription.info_demandee_at and not souscription.info_reponse_at)


def info_request_deadline(souscription: Souscription) -> Optional[datetime]:
    if not souscription.info_demandee_at:
        return None
    return souscription.info_demandee_at + timedelta(hours=settings.INFO_REQUEST_DELAY_HOURS)


def request_info(db: Session, souscription: Souscription, message: str, reviewer_id: int) -> Souscription:
    if souscription.statut != StatutSouscription.EN_ATTENTE_VALIDATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Des informations ne peuvent être demandées que pour un dossier en attente de validation.",
        )
    if info_request_pending(souscription):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Une demande d'informations est déjà en cours.")
    message = (message or "").strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Précisez les informations demandées.")
    souscription.info_demandee_at = datetime.utcnow()
    souscription.info_demandee_message = message
    souscription.info_demandee_par = reviewer_id
    souscription.info_rappel_envoye_at = None
    souscription.info_reponse = None
    souscription.info_reponse_at = None
    db.commit()
    db.refresh(souscription)
    # Aucun détail (potentiellement médical) dans l'aperçu : la demande est lue dans l'application.
    _notify(
        souscription.user_id,
        "souscription_info_requested",
        "Informations complémentaires demandées",
        f"MHC a besoin d'informations complémentaires pour votre souscription #{souscription.numero_souscription}. "
        f"Répondez dans l'application sous {settings.INFO_REQUEST_DELAY_HOURS} h.",
        souscription.id,
    )
    return souscription


def respond_info(db: Session, souscription: Souscription, reponse: str) -> Souscription:
    if not info_request_pending(souscription):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucune demande d'informations en cours.")
    if souscription.statut != StatutSouscription.EN_ATTENTE_VALIDATION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le dossier n'est plus en attente de validation.")
    reponse = (reponse or "").strip()
    if not reponse:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La réponse ne peut pas être vide.")
    souscription.info_reponse = reponse
    souscription.info_reponse_at = datetime.utcnow()
    db.commit()
    db.refresh(souscription)
    if souscription.info_demandee_par:
        _notify(
            souscription.info_demandee_par,
            "souscription_info_received",
            "Réponse reçue",
            f"L'assuré a répondu à la demande d'informations (souscription #{souscription.numero_souscription}).",
            souscription.id,
        )
    return souscription


def process_info_requests(db: Session, now: Optional[datetime] = None) -> dict:
    """Rappels avant échéance et refus automatiques des demandes restées sans réponse."""
    now = now or datetime.utcnow()
    pending = (
        db.query(Souscription)
        .filter(
            Souscription.statut == StatutSouscription.EN_ATTENTE_VALIDATION,
            Souscription.info_demandee_at.isnot(None),
            Souscription.info_reponse_at.is_(None),
        )
        .all()
    )
    reminders = rejected = 0
    for souscription in pending:
        deadline = info_request_deadline(souscription)
        if now >= deadline:
            reason = INFO_TIMEOUT_REASON.format(hours=settings.INFO_REQUEST_DELAY_HOURS)
            souscription.statut = StatutSouscription.REFUSEE
            souscription.validation_finale = "rejected"
            souscription.validation_finale_notes = reason
            souscription.validation_finale_date = now
            if souscription.validation_medicale == "pending":
                souscription.validation_medicale = "rejected"
            rejected += 1
            db.commit()
            _notify(
                souscription.user_id,
                "souscription_decision_result",
                "Souscription refusée",
                f"Votre souscription #{souscription.numero_souscription} a été refusée faute de réponse dans le délai. "
                "Le motif est consultable dans le détail de la souscription. Aucun paiement n'ayant été effectué, "
                "aucun remboursement n'est à prévoir.",
                souscription.id,
            )
            continue
        reminder_at = souscription.info_demandee_at + timedelta(hours=settings.INFO_REQUEST_REMINDER_HOURS)
        if now >= reminder_at and not souscription.info_rappel_envoye_at:
            souscription.info_rappel_envoye_at = now
            reminders += 1
            db.commit()
            remaining = max(1, int((deadline - now).total_seconds() // 3600))
            _notify(
                souscription.user_id,
                "souscription_info_reminder",
                "Rappel : informations attendues",
                f"Il vous reste environ {remaining} h pour répondre à la demande d'informations "
                f"de la souscription #{souscription.numero_souscription}, sans quoi elle sera refusée.",
                souscription.id,
            )
    return {"reminders": reminders, "rejected": rejected}


def expire_ended_policies(db: Session, now: Optional[datetime] = None) -> int:
    """Passe en « Expirée » les polices actives dont la période de couverture est terminée."""
    now = now or datetime.utcnow()
    # La date de fin est incluse dans la couverture (« De … à … ») : expiration
    # le lendemain à 00:00.
    start_of_today = datetime(now.year, now.month, now.day)
    ended = (
        db.query(Souscription)
        .filter(
            Souscription.statut == StatutSouscription.ACTIVE,
            Souscription.date_fin.isnot(None),
            Souscription.date_fin < start_of_today,
        )
        .all()
    )
    for souscription in ended:
        souscription.statut = StatutSouscription.EXPIREE
    if ended:
        db.commit()
    for souscription in ended:
        _notify(
            souscription.user_id,
            "souscription_expired",
            "Couverture terminée",
            f"La période de couverture de votre souscription #{souscription.numero_souscription} est terminée. "
            "Vos documents restent consultables dans l'historique.",
            souscription.id,
        )
    return len(ended)
