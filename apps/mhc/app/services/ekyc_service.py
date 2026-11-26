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


_PRE_PAYMENT_STATUSES = {
    StatutSouscription.EN_ATTENTE,
    StatutSouscription.PENDING,
    StatutSouscription.EN_ATTENTE_VALIDATION,
    StatutSouscription.EN_ATTENTE_PAIEMENT,
}


_EKYC_REVIEW_NOTE_PREFIX = "Vérification d'identité"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_session(
    db: Session,
    *,
    user: User,
    souscription: Souscription | None = None,
    flow: str = "TRAVEL_INSURANCE",
    metadata: dict[str, Any] | None = None,
    mobile: bool = False,
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

    # Destination OTP imposée (l'utilisateur ne peut pas la substituer).
    # Le téléphone est privilégié : la plateforme eKYC livre les codes par SMS
    # (canal configuré) — le canal email exige un SMTP qui n'est pas déployé.
    otp_destination = (
        user.telephone or user.numero_whatsapp or user.email or ""
    ).strip() or None

    # Le parcours eKYC s'ouvre dans un nouvel onglet : à la fin, le bouton
    # « Retour à l'application » ramène au wizard qui reprend l'étape courante
    # (eKYC si non vérifié, paiement sinon). Sans souscription → dashboard.
    # Client mobile : l'eKYC n'accepte qu'une URL http(s) — on passe par la
    # page relais ekyc-return.html qui rouvre l'app via le deep link mymhc://
    # (l'app revient au premier plan, son polling termine le parcours).
    front = (settings.FRONTEND_BASE_URL or "").rstrip("/")
    if mobile:
        return_url = (
            f"{front}/ekyc-return.html"
            + (f"?subscription_id={souscription.id}" if souscription else "")
            if front
            else None
        )
    else:
        return_url = (
            f"{front}/subscription-wizard.html?subscription_id={souscription.id}"
            if front and souscription
            else f"{front}/user-dashboard.html" if front else None
        )

    client = get_ekyc_client()
    response = client.create_session(
        customer_reference=customer_ref,
        flow=flow,
        metadata=meta,
        otp_destination=otp_destination,
        return_url=return_url,
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


_NON_TERMINAL_STATUSES = {"CREATED", "PENDING", "IN_PROGRESS", "PROCESSING", "OTP_SENT"}


def get_or_create_for_souscription(
    db: Session, *, user: User, souscription: Souscription, mobile: bool = False
) -> EkycSession:
    """Idempotent per souscription: a pending session is reused (the user
    resumes where they stopped); a terminal or expired one spawns a fresh
    attempt."""
    latest = (
        db.query(EkycSession)
        .filter(EkycSession.souscription_id == souscription.id)
        .order_by(EkycSession.created_at.desc())
        .first()
    )
    if latest is not None and latest.status in _NON_TERMINAL_STATUSES:
        expires = latest.expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires is None or expires > _now():
            return latest
    return create_session(db, user=user, souscription=souscription, flow="TRAVEL_INSURANCE", mobile=mobile)


def auto_create_for_voyage(
    db: Session, *, user: User, souscription: Souscription, mobile: bool = False
) -> EkycSession | None:
    """Trigger eKYC automatically after a travel-insurance subscription.
    Fail-soft: the ekyc platform being down must never break subscription
    creation — the session is retried when the user taps the CTA."""
    if not souscription.projet_voyage_id:
        return None
    try:
        return get_or_create_for_souscription(db, user=user, souscription=souscription, mobile=mobile)
    except Exception as exc:  # noqa: BLE001 — availability must not block the journey
        from logging import getLogger

        getLogger(__name__).warning(
            "eKYC auto-session failed for souscription %s: %s", souscription.id, exc
        )
        return None


def poll_result(db: Session, session: EkycSession) -> EkycResultResponse:
    """Interroge eKYC et met à jour la session locale."""
    client = get_ekyc_client()
    result = client.get_result(session.session_id)
    _update_session(db, session, result)
    return result


def refresh_session(db: Session, session: EkycSession) -> EkycResultResponse:
    """Polling persistant : enregistre le statut lu chez eKYC et applique le
    verdict quand il change vers un statut terminal — le parcours ne dépend
    plus de la seule arrivée du webhook."""
    previous = session.status
    result = poll_result(db, session)
    if result.is_terminal and result.status != previous:
        _apply_result(db, session, result)
        session.processed_at = _now()
    db.commit()
    db.refresh(session)
    return result


def identity_cleared(db: Session, souscription: Souscription) -> tuple[bool, EkycSession | None]:
    """Identité validée pour le paiement : dernière session VERIFIED, ou
    échec/revue eKYC levé ensuite par la revue production (décision produit :
    un échec eKYC part en revue manuelle, l'approbation débloque le paiement)."""
    latest = (
        db.query(EkycSession)
        .filter(EkycSession.souscription_id == souscription.id)
        .order_by(EkycSession.created_at.desc(), EkycSession.id.desc())
        .first()
    )
    if latest is None:
        return False, None
    if latest.status == "VERIFIED":
        return True, latest
    approved_at = souscription.validation_technique_date
    if (
        souscription.validation_technique == "approved"
        and souscription.validation_technique_par is not None
        and approved_at is not None
    ):
        failed = (
            db.query(EkycSession)
            .filter(
                EkycSession.souscription_id == souscription.id,
                EkycSession.status.in_(("REJECTED", "REVIEW")),
            )
            .all()
        )

        def _naive(value: datetime | None) -> datetime | None:
            return value.replace(tzinfo=None) if value is not None and value.tzinfo else value

        limit = _naive(approved_at)
        if failed and all((_naive(s.created_at) or limit) <= limit for s in failed):
            return True, latest
    return False, latest


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

    # Idempotence : un webhook rejoué pour un statut déjà appliqué est ignoré ;
    # un changement de verdict (ex. REVIEW → VERIFIED après correction par un
    # opérateur eKYC) doit en revanche être traité.
    if (
        session.webhook_received_at
        and session.processed_at
        and (payload.status is None or payload.status == session.status)
    ):
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
        if (
            souscription
            and result.status in ("REJECTED", "REVIEW")
            and souscription.statut in _PRE_PAYMENT_STATUSES
        ):
            # Échec ou indétermination eKYC → REVIEW MANUELLE (décision
            # produit) : le dossier part en revue production, jamais en
            # refus automatique. Aucun paiement n'est débité.
            if souscription.statut != StatutSouscription.EN_ATTENTE_VALIDATION:
                souscription.statut = StatutSouscription.EN_ATTENTE_VALIDATION
            souscription.validation_technique = "pending"
            souscription.validation_technique_notes = (
                f"{_EKYC_REVIEW_NOTE_PREFIX} {result.status} : revue manuelle requise"
            )
            db.flush()
        if souscription and result.is_verified:
            # Si la souscription est en attente de validation eKYC, on marque la
            # vérification d'identité comme terminée. La validation finale reste
            # déclenchée par les agents de production.
            ekyc_hold = souscription.validation_technique == "pending" and (
                souscription.validation_technique_notes or ""
            ).startswith(_EKYC_REVIEW_NOTE_PREFIX)
            if souscription.validation_technique in (None, "pending"):
                souscription.validation_technique = "approved"
                souscription.validation_technique_date = _now()
                souscription.validation_technique_notes = "Validé automatiquement via eKYC"
            # Le dossier n'était en revue qu'à cause d'un échec eKYC antérieur :
            # la nouvelle vérification réussie le rend au paiement (sinon il
            # reste « en attente de validation » sans aucune étape en attente).
            if (
                ekyc_hold
                and souscription.statut == StatutSouscription.EN_ATTENTE_VALIDATION
                and souscription.validation_medicale != "pending"
                and souscription.validation_finale != "pending"
                and "rejected" not in (souscription.validation_medicale, souscription.validation_finale)
            ):
                souscription.statut = StatutSouscription.EN_ATTENTE_PAIEMENT
                from app.services.subscription_decision_service import SubscriptionDecisionEngine

                SubscriptionDecisionEngine._notify_client_outcome(db, souscription, approved=True)
            db.flush()


def payment_block_reason(db: Session, souscription: Souscription) -> str | None:
    """Motif de blocage du paiement lié à l'eKYC (None = paiement autorisé).

    eKYC obligatoire pour les souscriptions voyage, même règle sur toutes
    les routes de paiement d'une souscription existante."""
    if not souscription.projet_voyage_id:
        return None
    cleared, latest = identity_cleared(db, souscription)
    if cleared:
        return None
    if latest and latest.status == "REVIEW":
        return (
            "Votre vérification d'identité est en cours d'analyse par nos équipes. "
            "Vous pourrez payer dès qu'elle sera validée."
        )
    if latest and latest.status in {"REJECTED", "EXPIRED"}:
        return (
            "Votre vérification d'identité a échoué ou a expiré. "
            "Veuillez la recommencer avant de payer."
        )
    return "La vérification d'identité (eKYC) est requise avant le paiement."


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
