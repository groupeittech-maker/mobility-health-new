"""Suppression des souscriptions non abouties (brouillons / approuvées non payées).

Règles (workflow MyMHC V3) :
- l'assuré peut supprimer manuellement une souscription « Brouillon » ou
  « À payer » depuis la liste « En attente » ;
- à défaut, ces souscriptions sont supprimées automatiquement à la fin du jour
  de la date de début de couverture souhaitée (cohérent avec « date passée
  interdite ») ; une suppression automatique ne classe jamais le dossier en
  « Expirées » ;
- rappels de suppression deux jours avant et la veille.

Une souscription dont un paiement est validé ou en cours chez le PSP n'est
jamais supprimée (le webhook AfriPaie doit pouvoir la retrouver).
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.enums import StatutPaiement, StatutSouscription
from app.models.notification import Notification
from app.models.paiement import Paiement
from app.models.souscription import Souscription

logger = logging.getLogger(__name__)

DELETABLE_STATUSES = (
    StatutSouscription.EN_ATTENTE,
    StatutSouscription.PENDING,
    StatutSouscription.EN_ATTENTE_PAIEMENT,
)
REMINDER_TYPE = "rappel_suppression_souscription"
REMINDER_DAYS_BEFORE = (2, 1)

_BLOCKING_PAYMENT_STATUSES = (StatutPaiement.VALIDE, StatutPaiement.EN_COURS)


def deletion_blocker(db: Session, souscription: Souscription) -> str | None:
    """Motif empêchant la suppression, ou None si elle est permise."""
    statut = souscription.statut
    statut_value = getattr(statut, "value", statut)
    if statut_value not in {s.value for s in DELETABLE_STATUSES}:
        return "Seules les souscriptions « Brouillon » ou « À payer » peuvent être supprimées"
    blocking = (
        db.query(Paiement.id)
        .filter(
            Paiement.souscription_id == souscription.id,
            Paiement.statut.in_(_BLOCKING_PAYMENT_STATUSES),
        )
        .first()
    )
    if blocking:
        return "Un paiement est en cours ou validé pour cette souscription"
    return None


def _start_day(souscription: Souscription) -> date | None:
    start = souscription.date_debut
    projet = getattr(souscription, "projet_voyage", None)
    if projet is not None and getattr(projet, "date_depart", None):
        start = projet.date_depart
    return start.date() if isinstance(start, datetime) else start


def purge_stale_subscriptions(db: Session, now: datetime | None = None) -> int:
    """Supprime les brouillons / « à payer » dont le jour de début souhaité est passé."""
    today = (now or datetime.utcnow()).date()
    candidates = db.query(Souscription).filter(Souscription.statut.in_(DELETABLE_STATUSES)).all()
    deleted = 0
    for souscription in candidates:
        start = _start_day(souscription)
        if start is None or start >= today or deletion_blocker(db, souscription):
            continue
        db.delete(souscription)
        deleted += 1
    if deleted:
        db.commit()
        logger.info("Purge souscriptions non abouties : %s supprimée(s)", deleted)
    return deleted


def _reminder_message(souscription: Souscription, days_left: int) -> tuple[str, str]:
    statut = getattr(souscription.statut, "value", souscription.statut)
    kind = "à payer" if statut == StatutSouscription.EN_ATTENTE_PAIEMENT.value else "en brouillon"
    when = "demain soir" if days_left == 1 else f"dans {days_left} jours"
    titre = "Votre souscription va être supprimée"
    message = (
        f"Votre souscription {souscription.numero_souscription} est {kind}. Elle sera supprimée "
        f"automatiquement {when} (fin du jour de début de couverture souhaité) si elle n'est pas finalisée."
    )
    return titre, message


def send_deletion_reminders(db: Session, now: datetime | None = None) -> int:
    """Rappels J-2 et J-1 avant la suppression automatique (un seul par échéance)."""
    from app.services.notification_service import NotificationService

    today = (now or datetime.utcnow()).date()
    sent = 0
    candidates = db.query(Souscription).filter(Souscription.statut.in_(DELETABLE_STATUSES)).all()
    for souscription in candidates:
        start = _start_day(souscription)
        if start is None or deletion_blocker(db, souscription):
            continue
        days_left = (start - today).days  # suppression à la fin du jour de début (J)
        if days_left not in REMINDER_DAYS_BEFORE:
            continue
        titre, message = _reminder_message(souscription, days_left)
        already = (
            db.query(Notification.id)
            .filter(
                Notification.user_id == souscription.user_id,
                Notification.type_notification == REMINDER_TYPE,
                Notification.lien_relation_id == souscription.id,
                Notification.message == message,
            )
            .first()
        )
        if already:
            continue
        try:
            NotificationService.create_notification(
                user_id=souscription.user_id,
                type_notification=REMINDER_TYPE,
                titre=titre,
                message=message,
                lien_relation_id=souscription.id,
                lien_relation_type="souscription",
                channels=["push"],
            )
            sent += 1
        except Exception as exc:  # pragma: no cover - notification best effort
            logger.warning("Rappel de suppression impossible (souscription %s) : %s", souscription.id, exc)
    return sent
