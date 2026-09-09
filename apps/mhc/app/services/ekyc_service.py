"""Service d'intégration eKYC pour MHC.

Couche métier au-dessus de ``app.integrations.ekyc`` : crée une session,
stocke son état local, vérifie les webhooks et applique le résultat à l'utilisateur
ou à la souscription.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import StatutSouscription
from app.integrations.ekyc import get_ekyc_client, verify_ekyc_webhook
from app.integrations.ekyc.schemas import EkycResultResponse, EkycWebhookPayload
from app.models.ekyc_session import EkycSession
from app.models.souscription import Souscription
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_session(
    db: Session,
    *,
    user: User,
    souscription: Souscription | None = None,
    flow: str = "TRAVEL_INSURANCE",
    metadata: dict[str, Any] | None = None,
) -> EkycSession:
    """Créer une session eKYC et la persister localement.

    ``customer_reference`` est choisie pour être réversible depuis le webhook :
    ``user-<id>`` (éventuellement suffixé par la souscription).
    """
    customer_ref = f"user-{user.id}"
    if souscription:
        customer_ref = f"user-{user.id}-sub-{souscription.id}"

    meta = metadata or {}
    meta["mhc_user_id"] = user.id
    if souscription:
        meta["mhc_souscription_id"] = souscription.id

    client = get_ekyc_client()
    response = client.create_session(
        customer_reference=customer_ref,
        flow=flow,
        metadata=meta,
    )

    session = EkycSession(
        session_id=response.session_id,
        customer_reference=customer_ref,
        user_id=user.id,
        souscription_id=souscription.id if souscription else None,
        flow=response.flow,
        status=response.status,
        verification_url=response.verification_url,
        expires_at=_parse_iso(response.expires_at),
        identity=None,
        checks=None,
        reasons=None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def poll_result(db: Session, session: EkycSession) -> EkycResultResponse:
    """Interroge eKYC et met à jour la session locale."""
    client = get_ekyc_client()
    result = client.get_result(session.session_id)
    _update_session(db, session, result)
    return result


def handle_webhook(
    db: Session,
    headers: dict[str, str],
    body: bytes,
) -> EkycSession:
    """Vérifie et traite un webhook eKYC entrant.

    Lève une exception si la signature est invalide ou si le timestamp est hors
    tolérance. Idempotente : si la session a déjà été traitée, elle est retournée
    sans ré-appliquer les effets métier.
    """
    secret = settings.EKYC_WEBHOOK_SECRET
    if not secret:
        raise RuntimeError("EKYC_WEBHOOK_SECRET non configuré")

    from app.integrations.ekyc import extract_ekyc_webhook_headers

    signature, timestamp = extract_ekyc_webhook_headers(headers)
    payload = verify_ekyc_webhook(secret, body, signature, timestamp)

    session = db.query(EkycSession).filter_by(session_id=payload.session_id).first()
    if session is None:
        # On tente de réconcilier par customer_reference si présent.
        if payload.customer_reference:
            session = db.query(EkycSession).filter_by(
                customer_reference=payload.customer_reference
            ).first()
        if session is None:
            raise ValueError(f"Session eKYC inconnue: {payload.session_id}")

    # Idempotence
    if session.webhook_received_at and session.processed_at:
        return session

    session.webhook_received_at = _now()

    # Rafraîchir le résultat depuis eKYC pour obtenir l'identité minimisée
    # (le webhook ne contient que le statut).
    try:
        result = poll_result(db, session)
    except Exception:
        # Si le poll échoue, on propage quand même le statut du webhook.
        result = EkycResultResponse(
            session_id=payload.session_id,
            customer_reference=payload.customer_reference,
            flow=payload.flow or session.flow,
            status=payload.status or "REVIEW",
            checks=session.checks or {},
            reasons=session.reasons or [],
        )
        _update_session(db, session, result)

    _apply_result(db, session, result, payload)
    session.processed_at = _now()
    db.commit()
    db.refresh(session)
    return session


def _update_session(db: Session, session: EkycSession, result: EkycResultResponse) -> None:
    session.status = result.status
    session.checks = result.checks
    session.reasons = result.reasons
    session.identity = (
        result.identity.model_dump(mode="json", exclude_none=True) if result.identity else None
    )
    session.completed_at = _parse_iso(result.completed_at)
    db.flush()


def _apply_result(
    db: Session,
    session: EkycSession,
    result: EkycResultResponse,
    payload: EkycWebhookPayload | None = None,
) -> None:
    """Applique le verdict eKYC aux objets MHC liés."""
    if session.user_id:
        user = db.get(User, session.user_id)
        if user and result.identity:
            identity = result.identity
            user.nationalite = identity.nationality or user.nationalite
            user.numero_passeport = identity.document_number or user.numero_passeport
            if identity.expiry_date:
                try:
                    user.validite_passeport = datetime.fromisoformat(identity.expiry_date).date()
                except ValueError:
                    pass
            db.flush()

    if session.souscription_id:
        souscription = db.get(Souscription, session.souscription_id)
        if souscription and result.is_verified:
            # Si la souscription est en attente de validation eKYC, on marque la
            # vérification d'identité comme terminée. La validation finale reste
            # déclenchée par les agents de production.
            if souscription.validation_technique in (None, "pending"):
                souscription.validation_technique = "approved"
                souscription.validation_technique_date = _now()
                souscription.validation_technique_notes = "Validé automatiquement via eKYC"
            db.flush()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
