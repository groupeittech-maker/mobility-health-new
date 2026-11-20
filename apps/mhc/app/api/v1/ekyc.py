"""API eKYC pour MHC : création de session, polling du résultat, réception webhook."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.ekyc_session import EkycSession
from app.models.souscription import Souscription
from app.models.user import User
from app.schemas.ekyc import (
    EkycSessionCreate,
    EkycSessionResponse,
    EkycWebhookResponse,
)
from app.services import ekyc_service

router = APIRouter(tags=["ekyc"])


def _is_mobile_client(request: Request) -> bool:
    return (request.headers.get("x-client-platform") or "").strip().lower() == "mobile"


@router.post("/ekyc/sessions", status_code=status.HTTP_201_CREATED, response_model=EkycSessionResponse)
def create_ekyc_session(
    payload: EkycSessionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EkycSessionResponse:
    """L'utilisateur authentifié démarre une vérification d'identité eKYC.

    Retourne l'URL de vérification hébergée par la plateforme eKYC à ouvrir
    dans le navigateur / webview de l'utilisateur.
    """
    souscription = None
    if payload.souscription_id:
        souscription = db.get(Souscription, payload.souscription_id)
        if souscription is None or souscription.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Souscription invalide ou non autorisée",
            )

    mobile = _is_mobile_client(request)
    session = ekyc_service.get_or_create_for_souscription(
        db,
        user=current_user,
        souscription=souscription,
        mobile=mobile,
    ) if souscription else ekyc_service.create_session(
        db,
        user=current_user,
        souscription=None,
        flow="TRAVEL_INSURANCE",
        mobile=mobile,
    )

    return EkycSessionResponse(
        session_id=session.session_id,
        status=session.status,
        verification_url=session.verification_url,
        expires_at=session.expires_at.isoformat() if session.expires_at else None,
    )


@router.get("/ekyc/sessions/by-souscription/{souscription_id}")
def get_latest_ekyc_for_souscription(
    souscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Dernière session eKYC liée à une souscription — utilisée par le CTA
    « Vérifier mon identité » du détail de souscription (mode pilote :
    visible tant que le dernier verdict n'est pas VERIFIED)."""
    souscription = db.get(Souscription, souscription_id)
    if souscription is None or souscription.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Souscription non autorisée")
    session = (
        db.query(EkycSession)
        .filter(EkycSession.souscription_id == souscription_id)
        .order_by(EkycSession.created_at.desc())
        .first()
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucune session eKYC")
    return {
        "session_id": session.session_id,
        "status": session.status,
        "verification_url": session.verification_url,
        "is_verified": session.status == "VERIFIED",
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
    }


@router.get("/ekyc/sessions/{session_id}")
def get_ekyc_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Récupère l'état d'une session eKYC (avec polling live si non terminal)."""
    session = db.query(EkycSession).filter_by(
        session_id=session_id, user_id=current_user.id
    ).first()
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session eKYC introuvable")

    result = ekyc_service.poll_result(db, session)
    return {
        "session_id": result.session_id,
        "status": result.status,
        "checks": result.checks,
        "reasons": result.reasons,
        "identity": result.identity.model_dump(mode="json", exclude_none=True) if result.identity else None,
        "is_terminal": result.is_terminal,
        "is_verified": result.is_verified,
    }


@router.post("/webhooks/ekyc")
async def receive_ekyc_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> EkycWebhookResponse:
    """Endpoint public recevant les webhooks de la plateforme eKYC.

    Vérifie la signature HMAC, met à jour la session et applique le verdict.
    """
    body = await request.body()
    headers = dict(request.headers)

    try:
        ekyc_service.handle_webhook(db, headers, body)
    except Exception as exc:
        # On loggue sans dévoiler les détails ; on retourne 400 pour que eKYC retry.
        from logging import getLogger

        logger = getLogger(__name__)
        logger.warning("Webhook eKYC rejeté: %s", exc)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Webhook rejeté") from exc

    return EkycWebhookResponse(status="accepted")


_EKYC_REVIEW_ROLES = {
    "admin",
    "production_agent",
    "agent_conformite_production",
    "medecin_referent_mh",
    "superviseur_technique",
}


def _require_ekyc_reviewer(current_user: User = Depends(get_current_user)) -> User:
    """Revue eKYC : mêmes acteurs que la revue de dossier (production,
    conformité, médical référent, superviseur) + admin."""
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role not in _EKYC_REVIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux équipes de revue",
        )
    return current_user


def _latest_session_for_souscription(db: Session, souscription_id: int) -> EkycSession:
    session = (
        db.query(EkycSession)
        .filter(EkycSession.souscription_id == souscription_id)
        .order_by(EkycSession.created_at.desc())
        .first()
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucune session eKYC pour cette souscription")
    return session


@router.get("/admin/ekyc/by-souscription/{souscription_id}/evidence")
def ekyc_evidence_for_souscription(
    souscription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_require_ekyc_reviewer),
):
    """Dossier de preuve eKYC pour la revue : statut, checks détaillés
    (scores/raisons) et liste des pièces (photo document, selfie…).

    Les images ne transitent jamais par le navigateur avec les credentials
    eKYC — MHC les proxyfie via ``/admin/ekyc/{session}/artifacts/{id}``.
    """
    session = _latest_session_for_souscription(db, souscription_id)
    from app.integrations.ekyc import get_ekyc_client

    client = get_ekyc_client()
    try:
        evidence = client.get_evidence(session.session_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Dossier eKYC indisponible: {exc}",
        ) from exc
    return {
        "session_id": session.session_id,
        "status": evidence.status or session.status,
        "checks": evidence.checks,
        "check_details": evidence.check_details,
        "reasons": evidence.reasons,
        "identity": evidence.identity,
        "risk_score": evidence.risk_score,
        "artifacts": [
            {
                **a.model_dump(),
                "url": f"/api/v1/admin/ekyc/sessions/{session.session_id}/artifacts/{a.artifact_id}",
            }
            for a in evidence.artifacts
        ],
        "certificate_url": f"/api/v1/admin/ekyc/sessions/{session.session_id}/certificate",
    }


@router.get("/admin/ekyc/sessions/{session_id}/artifacts/{artifact_id}")
def ekyc_artifact(
    session_id: str,
    artifact_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_require_ekyc_reviewer),
):
    """Proxy authentifié vers une pièce de preuve eKYC (image)."""
    from fastapi.responses import Response

    from app.integrations.ekyc import get_ekyc_client

    if db.query(EkycSession).filter_by(session_id=session_id).first() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session eKYC introuvable")
    try:
        content, media_type = get_ekyc_client().get_artifact(session_id, artifact_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Pièce eKYC indisponible: {exc}",
        ) from exc
    return Response(content=content, media_type=media_type)


@router.get("/admin/ekyc/sessions/{session_id}/certificate")
def ekyc_certificate(
    session_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_require_ekyc_reviewer),
):
    """Proxy authentifié vers le certificat KYC signé (PDF officiel)."""
    from fastapi.responses import Response

    from app.integrations.ekyc import get_ekyc_client

    if db.query(EkycSession).filter_by(session_id=session_id).first() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session eKYC introuvable")
    try:
        pdf = get_ekyc_client().get_certificate(session_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Certificat eKYC indisponible: {exc}",
        ) from exc
    return Response(content=pdf, media_type="application/pdf")
