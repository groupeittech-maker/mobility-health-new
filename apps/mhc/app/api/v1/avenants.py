"""Actions sur une police (annulation, modification, prorogation), avenants et ristournes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.permissions import F_REMBOURSEMENT, LEVEL_CONSULTATION, LEVEL_EDITION, has_permission
from app.models.avenant import Avenant
from app.models.ristourne import Ristourne
from app.models.souscription import Souscription
from app.models.user import User
from app.schemas.avenant import (
    AnnulationRequest,
    AvenantPaymentRequest,
    AvenantResponse,
    ModificationRequest,
    PolicyActionResult,
    PolicyActionsResponse,
    ProrogationRequest,
    RistourneConfirmRequest,
    RistourneResponse,
)
from app.services import avenant_service
from app.services.avenant_service import ActionResult, AvenantError

router = APIRouter()

# Profils internes habilités à consulter les avenants de toutes les polices.
STAFF_ROLES = {
    "admin",
    "production_agent",
    "superviseur_technique",
    "agent_conformite_production",
    "agent_sinistre_assureur",
}



def _role(user: User) -> str:
    role = getattr(user, "role", None)
    return str(getattr(role, "value", role) or "")


def _is_admin(user: User) -> bool:
    return _role(user) == "admin" or bool(getattr(user, "is_superuser", False))


def _is_staff(user: User) -> bool:
    return _is_admin(user) or _role(user) in STAFF_ROLES


def _is_finance(user: User, level: str = LEVEL_CONSULTATION) -> bool:
    """Remboursements (ristournes) : fonctionnalité « remboursement » de la matrice BO."""
    return _is_admin(user) or has_permission(_role(user), F_REMBOURSEMENT, level)


def _get_souscription(db: Session, souscription_id: int) -> Souscription:
    sous = db.query(Souscription).filter(Souscription.id == souscription_id).first()
    if not sous:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souscription introuvable.")
    return sous


def _owned_souscription(db: Session, souscription_id: int, user: User) -> Souscription:
    """Les actions sur une police sont réservées à l'assuré principal (ou admin)."""
    sous = _get_souscription(db, souscription_id)
    if not (_is_admin(user) or sous.user_id == user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul l'assuré principal peut agir sur cette police.")
    return sous


def _readable_souscription(db: Session, souscription_id: int, user: User) -> Souscription:
    sous = _get_souscription(db, souscription_id)
    if not (_is_staff(user) or _is_finance(user) or sous.user_id == user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cette police.")
    return sous


def _statut(sous: Souscription) -> str:
    return getattr(sous.statut, "value", sous.statut)


def _result(result: ActionResult) -> PolicyActionResult:
    montants = None
    if result.montants is not None:
        m = result.montants
        montants = {"prime": m.prime, "frais_police": m.frais_police, "frais_services": m.frais_services, "taxes": m.taxes, "total": m.total}
    paiement = result.paiement
    return PolicyActionResult(
        souscription_id=result.souscription.id,
        statut_souscription=_statut(result.souscription),
        simulation=result.simulation,
        nature_ajustement=result.nature,
        montants=montants,
        avenant=AvenantResponse.model_validate(result.avenant) if result.avenant else None,
        ristourne=RistourneResponse.model_validate(result.ristourne) if result.ristourne else None,
        paiement_id=getattr(paiement, "id", None),
        payment_status=getattr(getattr(paiement, "statut", None), "value", None),
        payment_url=result.payment_info.get("checkout_url"),
        payment_instructions=result.payment_info.get("instructions"),
    )


def _run(db: Session, fn, *args, **kwargs) -> PolicyActionResult:
    try:
        result = fn(db, *args, **kwargs)
    except AvenantError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result.simulation:
        db.rollback()
    else:
        db.commit()
        db.refresh(result.souscription)
    return _result(result)


# ---------------------------------------------------------------------------
# Actions sur une police
# ---------------------------------------------------------------------------
@router.get("/subscriptions/{subscription_id}/actions", response_model=PolicyActionsResponse)
async def get_policy_actions(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actions disponibles (règle exclusive), demande en cours, avenants et ristournes."""
    sous = _readable_souscription(db, subscription_id, current_user)
    info = avenant_service.available_actions(db, sous)
    return PolicyActionsResponse(
        souscription_id=sous.id,
        statut_souscription=_statut(sous),
        actions=info["actions"],
        action_en_cours=info["action_en_cours"],
        duree_max_jours=info["duree_max_jours"],
        avenants=avenant_service.list_avenants(db, sous.id),
        ristournes=avenant_service.list_ristournes(db, sous.id),
    )


@router.post("/subscriptions/{subscription_id}/actions/annulation", response_model=PolicyActionResult)
async def request_annulation(
    subscription_id: int,
    body: AnnulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Annulation avant la date d'effet (avenant 102). `confirmer=false` : simulation."""
    sous = _owned_souscription(db, subscription_id, current_user)
    return _run(db, avenant_service.request_annulation, sous, current_user, confirm=body.confirmer, motif=body.motif)


@router.post("/subscriptions/{subscription_id}/actions/modification", response_model=PolicyActionResult)
async def request_modification(
    subscription_id: int,
    body: ModificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Modification des dates avant la date d'effet (avenant 107). `confirmer=false` : simulation."""
    sous = _owned_souscription(db, subscription_id, current_user)
    return _run(
        db, avenant_service.request_modification, sous, current_user,
        nouvelle_date_debut=body.nouvelle_date_debut,
        nouvelle_date_fin=body.nouvelle_date_fin,
        confirm=body.confirmer,
        motif=body.motif,
    )


@router.post("/subscriptions/{subscription_id}/actions/prorogation", response_model=PolicyActionResult)
async def request_prorogation(
    subscription_id: int,
    body: ProrogationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Prolongation jusqu'à une nouvelle date de fin (avenant 108). `confirmer=false` : simulation."""
    sous = _owned_souscription(db, subscription_id, current_user)
    return _run(
        db, avenant_service.request_prorogation, sous, current_user,
        nouvelle_date_fin=body.nouvelle_date_fin,
        confirm=body.confirmer,
        motif=body.motif,
    )


def _owned_avenant(db: Session, avenant_id: int, user: User) -> Avenant:
    avenant = avenant_service.get_avenant(db, avenant_id)
    if not avenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avenant introuvable.")
    _owned_souscription(db, avenant.souscription_id, user)
    return avenant


@router.post("/avenants/{avenant_id}/payer", response_model=PolicyActionResult)
async def pay_avenant(
    avenant_id: int,
    body: AvenantPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Paiement du complément de prime (modification / prorogation)."""
    avenant = _owned_avenant(db, avenant_id, current_user)
    payer = avenant.souscription.user if avenant.souscription else current_user
    return _run(db, lambda session: avenant_service.start_avenant_payment(
        session, avenant, payer, payment_type=body.payment_type, flow=body.flow,
    ))


@router.post("/avenants/{avenant_id}/abandon", response_model=AvenantResponse)
async def abandon_avenant(
    avenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """L'assuré renonce à une demande en attente de paiement : les actions sont réactivées."""
    avenant = _owned_avenant(db, avenant_id, current_user)
    try:
        avenant_service.abandon_pending(db, avenant, "Demande abandonnée par l'assuré.")
    except AvenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(avenant)
    return avenant


# ---------------------------------------------------------------------------
# Consultation des avenants
# ---------------------------------------------------------------------------
@router.get("/avenants", response_model=list[AvenantResponse])
async def list_all_avenants(
    statut: Optional[str] = None,
    type_avenant: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_staff(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux équipes MHC.")
    query = db.query(Avenant).filter(Avenant.type_avenant.in_(avenant_service.ACTION_TYPES))
    if statut:
        query = query.filter(Avenant.statut == statut)
    if type_avenant:
        query = query.filter(Avenant.type_avenant == type_avenant)
    return query.order_by(Avenant.created_at.desc()).limit(200).all()


@router.get("/subscriptions/{subscription_id}/avenants", response_model=list[AvenantResponse])
async def list_subscription_avenants(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _readable_souscription(db, subscription_id, current_user)
    return avenant_service.list_avenants(db, subscription_id)


def _pdf_response(pdf, filename: str) -> Response:
    return Response(
        content=pdf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename.replace("/", "-")}"'},
    )


@router.get("/avenants/{avenant_id}/download")
async def download_avenant(
    avenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """PDF de l'avenant émis (régénéré, toujours à jour)."""
    avenant = avenant_service.get_avenant(db, avenant_id)
    if not avenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avenant introuvable.")
    _readable_souscription(db, avenant.souscription_id, current_user)
    try:
        pdf = avenant_service.build_avenant_pdf(db, avenant)
    except AvenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _pdf_response(pdf, f"avenant-{avenant.numero}.pdf")


# ---------------------------------------------------------------------------
# Ristournes (remboursements) — confirmées par la finance MHC
# ---------------------------------------------------------------------------
@router.get("/ristournes", response_model=list[RistourneResponse])
async def list_ristournes(
    statut: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_finance(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé à la finance MHC.")
    query = db.query(Ristourne)
    if statut:
        query = query.filter(Ristourne.statut == statut)
    return query.order_by(Ristourne.created_at.desc()).limit(500).all()


@router.post("/ristournes/{ristourne_id}/confirmer", response_model=RistourneResponse)
async def confirm_ristourne(
    ristourne_id: int,
    body: RistourneConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """La finance confirme le remboursement effectué → quittance de ristourne (120)."""
    if not _is_finance(current_user, LEVEL_EDITION):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seule la finance MHC peut confirmer un remboursement.")
    ristourne = db.query(Ristourne).filter(Ristourne.id == ristourne_id).first()
    if not ristourne:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remboursement introuvable.")
    try:
        avenant_service.confirm_ristourne(
            db, ristourne, current_user,
            moyen_remboursement=body.moyen_remboursement, reference=body.reference,
        )
    except AvenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(ristourne)
    return ristourne


@router.get("/ristournes/{ristourne_id}/download")
async def download_ristourne(
    ristourne_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """PDF de la quittance de ristourne (après confirmation du remboursement)."""
    ristourne = db.query(Ristourne).filter(Ristourne.id == ristourne_id).first()
    if not ristourne:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remboursement introuvable.")
    _readable_souscription(db, ristourne.souscription_id, current_user)
    try:
        pdf = avenant_service.build_ristourne_pdf(db, ristourne)
    except AvenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _pdf_response(pdf, f"quittance-ristourne-{ristourne.numero}.pdf")
