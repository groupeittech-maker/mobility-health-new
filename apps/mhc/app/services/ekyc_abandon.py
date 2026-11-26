"""Relance et abandon des souscriptions bloquées par une session eKYC morte.

Règles (workflow MyMHC V3) :
- quand la dernière session eKYC d'une souscription « en attente » meurt
  (REJECTED / EXPIRED / autre statut terminal), l'assuré reçoit une
  notification explicite l'invitant à relancer la vérification ;
- 30 min avant l'échéance, un rappel est envoyé ;
- si 2 h après la dernière activité eKYC la vérification n'est toujours pas
  terminée, la souscription passe en « Expirée » (session abandonnée) et ne
  peut plus être poursuivie — l'assuré doit repartir sur une nouvelle
  souscription.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.enums import StatutSouscription
from app.models.ekyc_session import EkycSession
from app.models.notification import Notification
from app.models.souscription import Souscription
from app.services.subscription_lifecycle import _notify

logger = logging.getLogger(__name__)

# Statuts eKYC qui laissent encore une chance de terminer le parcours.
_NON_TERMINAL_STATUSES = {"CREATED", "PENDING", "IN_PROGRESS", "PROCESSING", "OTP_SENT"}

ABANDON_DELAY = timedelta(hours=2)
PRE_EXPIRY_REMINDER = timedelta(minutes=30)

RELANCE_TYPE = "ekyc_relance"
RAPPEL_TYPE = "ekyc_relance_echeance"
ABANDON_TYPE = "ekyc_abandon"

_TRACKED_SOUSCRIPTION_STATUTS = (
    StatutSouscription.EN_ATTENTE,
    StatutSouscription.PENDING,
)


def _has_notification(
    db: Session, user_id: int, type_notification: str, souscription_id: int, since: datetime
) -> bool:
    return (
        db.query(Notification.id)
        .filter(
            Notification.user_id == user_id,
            Notification.type_notification == type_notification,
            Notification.lien_relation_id == souscription_id,
            Notification.lien_relation_type == "souscription",
            Notification.created_at >= since,
        )
        .first()
        is not None
    )


def _session_still_alive(session: EkycSession, now: datetime) -> bool:
    if session.status not in _NON_TERMINAL_STATUSES:
        return False
    if session.expires_at is not None:
        return session.expires_at > now
    # Session « vivante » sans date d'expiration connue : si elle n'a pas bougé
    # dans le délai d'abandon, le parcours est considéré mort (webhook jamais reçu).
    last_move = session.updated_at or session.created_at
    return last_move is not None and last_move > now - ABANDON_DELAY


def _reference_activity(souscription: Souscription, session: Optional[EkycSession]) -> datetime:
    """Dernière activité eKYC connue : fin de la dernière session, sinon la
    dernière touche de la souscription (session jamais créée)."""
    if session is not None:
        return session.updated_at or session.created_at or souscription.created_at
    return souscription.updated_at or souscription.created_at


def process_ekyc_abandons(db: Session, now: Optional[datetime] = None) -> dict:
    """Scanne les souscriptions « en attente » dont l'eKYC est mort.

    Retourne un rapport {relances, rappels, abandonnees} pour le monitoring.
    """
    now = now or datetime.utcnow()
    report = {"relances": 0, "rappels": 0, "abandonnees": 0, "scanned": 0}

    souscriptions = (
        db.query(Souscription)
        .filter(Souscription.statut.in_(_TRACKED_SOUSCRIPTION_STATUTS))
        .all()
    )
    report["scanned"] = len(souscriptions)

    for souscription in souscriptions:
        latest = (
            db.query(EkycSession)
            .filter(EkycSession.souscription_id == souscription.id)
            .order_by(EkycSession.created_at.desc())
            .first()
        )
        if latest is not None and _session_still_alive(latest, now):
            continue  # parcours eKYC en cours — la session expire d'elle-même

        reference = _reference_activity(souscription, latest)
        elapsed = now - reference
        if elapsed < timedelta(0):
            continue
        deadline = ABANDON_DELAY - elapsed
        numero = souscription.numero_souscription or str(souscription.id)

        if deadline <= timedelta(0):
            souscription.statut = StatutSouscription.EXPIREE
            if not _has_notification(db, souscription.user_id, ABANDON_TYPE, souscription.id, reference):
                _notify(
                    souscription.user_id,
                    ABANDON_TYPE,
                    "Souscription expirée",
                    "Votre souscription "
                    f"{numero} a été clôturée : la vérification d'identité n'a "
                    "pas été terminée dans le délai imparti. Créez une nouvelle "
                    "souscription pour repartir sur un dossier actif.",
                    souscription.id,
                )
            report["abandonnees"] += 1
            continue

        if deadline <= PRE_EXPIRY_REMINDER:
            if not _has_notification(db, souscription.user_id, RAPPEL_TYPE, souscription.id, reference):
                _notify(
                    souscription.user_id,
                    RAPPEL_TYPE,
                    "Plus que 30 minutes pour vérifier votre identité",
                    "Votre souscription "
                    f"{numero} sera clôturée si la vérification d'identité "
                    "n'est pas terminée dans les 30 prochaines minutes. "
                    "Relancez-la depuis votre souscription.",
                    souscription.id,
                )
                report["rappels"] += 1
            continue

        if latest is not None and not _has_notification(
            db, souscription.user_id, RELANCE_TYPE, souscription.id, reference
        ):
            raison = "expirée" if latest.status == "EXPIRED" else "abouti à un échec"
            _notify(
                souscription.user_id,
                RELANCE_TYPE,
                "Vérification d'identité à reprendre",
                "La vérification d'identité de votre souscription "
                f"{numero} a {raison}. Relancez-la depuis votre souscription "
                "pour continuer — le dossier sera clôturé après 2 heures "
                "d'inactivité.",
                souscription.id,
            )
            report["relances"] += 1

    return report
