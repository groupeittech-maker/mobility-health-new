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


@router.post("/ekyc/sessions", status_code=status.HTTP_201_CREATED, response_model=EkycSessionResponse)
def create_ekyc_session(
    payload: EkycSessionCreate,
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

    session = ekyc_service.get_or_create_for_souscription(
        db,
        user=current_user,
        souscription=souscription,
    ) if souscription else ekyc_service.create_session(
        db,
        user=current_user,
        souscription=None,
        flow="TRAVEL_INSURANCE",
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
