"""Endpoints des avenants de police : suspension, réémission, téléchargement."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.souscription import Souscription
from app.models.user import User
from app.schemas.avenant import (
    AvenantCatalogResponse,
    AvenantReemissionRequest,
    AvenantResponse,
    AvenantSuspensionDecision,
    AvenantSuspensionRequest,
)
from app.services.avenant_service import (
    AvenantError,
    build_avenant_pdf,
    decide_suspension,
    get_avenant,
    issue_reemission,
    list_avenants,
    request_suspension,
)
from app.services.official_travel_documents import (
    AVENANT_SUSPENSION_MOTIFS,
    AVENANT_SUSPENSION_PIECES,
)

router = APIRouter()

# Rôle(s) « Assureur » habilités à décider de la suspension / réémission.
ASSUREUR_DECISION_ROLES = {"agent_sinistre_assureur", "admin"}


def _role(user: User) -> str:
    role = getattr(user, "role", None)
    return str(getattr(role, "value", role) or "")


def _is_admin(user: User) -> bool:
    return _role(user) == "admin" or getattr(user, "is_superuser", False)


def _get_souscription(db: Session, souscription_id: int) -> Souscription:
    sous = db.query(Souscription).filter(Souscription.id == souscription_id).first()
    if not sous:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souscription introuvable.")
    return sous


@router.get("/avenants/catalogue", response_model=AvenantCatalogResponse)
async def get_avenant_catalog(current_user: User = Depends(get_current_user)):
    """Motifs et pièces justificatives possibles pour une demande de suspension."""
    return AvenantCatalogResponse(motifs=AVENANT_SUSPENSION_MOTIFS, pieces=AVENANT_SUSPENSION_PIECES)


@router.get("/subscriptions/{subscription_id}/avenants", response_model=list[AvenantResponse])
async def list_subscription_avenants(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sous = _get_souscription(db, subscription_id)
    if not (_is_admin(current_user) or _role(current_user) in ASSUREUR_DECISION_ROLES or sous.user_id == current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à ces avenants.")
    return list_avenants(db, subscription_id)


@router.post(
    "/subscriptions/{subscription_id}/avenant-suspension",
    response_model=AvenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_avenant_suspension(
    subscription_id: int,
    body: AvenantSuspensionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Le souscripteur (ou un admin) demande la suspension de la police."""
    sous = _get_souscription(db, subscription_id)
    if not (_is_admin(current_user) or sous.user_id == current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul le souscripteur peut demander la suspension.")
    try:
        avenant = request_suspension(
            db, sous, current_user,
            motifs=body.motifs, motif_autre=body.motif_autre, pieces=body.pieces,
        )
    except AvenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(avenant)
    return avenant


@router.post("/avenants/{avenant_id}/suspension-decision", response_model=AvenantResponse)
async def decide_avenant_suspension(
    avenant_id: int,
    body: AvenantSuspensionDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """L'Assureur (agent_sinistre_assureur) valide ou refuse la suspension."""
    if not (_is_admin(current_user) or _role(current_user) in ASSUREUR_DECISION_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul l'Assureur peut valider une suspension.")
    avenant = get_avenant(db, avenant_id)
    if not avenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avenant introuvable.")
    try:
        decide_suspension(db, avenant, current_user, approve=body.approve, date_effet=body.date_effet, notes=body.notes)
    except AvenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(avenant)
    return avenant


@router.post(
    "/subscriptions/{subscription_id}/avenant-reemission",
    response_model=AvenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_avenant_reemission(
    subscription_id: int,
    body: AvenantReemissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """L'Assureur lève la suspension : réémission de la police."""
    if not (_is_admin(current_user) or _role(current_user) in ASSUREUR_DECISION_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul l'Assureur peut réémettre la police.")
    sous = _get_souscription(db, subscription_id)
    try:
        avenant = issue_reemission(db, sous, current_user, date_effet=body.date_effet)
    except AvenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(avenant)
    return avenant


@router.get("/avenants/{avenant_id}/download")
async def download_avenant(
    avenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Télécharge le PDF de l'avenant (régénéré, toujours à jour)."""
    avenant = get_avenant(db, avenant_id)
    if not avenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avenant introuvable.")
    sous = db.query(Souscription).filter(Souscription.id == avenant.souscription_id).first()
    if not (_is_admin(current_user) or _role(current_user) in ASSUREUR_DECISION_ROLES or (sous and sous.user_id == current_user.id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cet avenant.")
    try:
        pdf = build_avenant_pdf(db, avenant)
    except AvenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    filename = f"avenant-{avenant.numero}.pdf".replace("/", "-")
    return Response(
        content=pdf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
