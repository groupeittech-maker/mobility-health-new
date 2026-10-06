from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.enums import Role
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.sinistre import Sinistre
from app.models.alerte import Alerte
from app.models.souscription import Souscription
from app.models.courtier_agent import CourtierAgent
from app.schemas.sinistre import SinistreResponse, SinistreWorkflowStepResponse
from app.services.sinistre_workflow_service import ensure_workflow_steps

router = APIRouter()


def _get_courtier_id_for_agent(db: Session, current_user: User, agent_types) -> Optional[int]:
    """Récupère l'ID du courtier associé à un agent."""
    try:
        courtier_agent = db.query(CourtierAgent).filter(
            CourtierAgent.user_id == current_user.id,
            CourtierAgent.type_agent.in_(agent_types),
        ).first()
        if courtier_agent:
            return courtier_agent.courtier_id
    except Exception:
        pass
    return None


def require_agent_sinistre_courtier(current_user: User = Depends(get_current_user)) -> User:
    """Vérifie que l'utilisateur est agent sinistre d'un courtier."""
    if current_user.role != Role.AGENT_SINISTRE_COURTIER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Agent sinistre courtier access required.",
        )
    return current_user


def _check_sinistre_scope(sinistre: Sinistre, courtier_id: int) -> None:
    if sinistre.souscription_id:
        souscription_courtier_id = (
            sinistre.souscription.courtier_id if sinistre.souscription
            else None
        )
        if souscription_courtier_id is not None and souscription_courtier_id != courtier_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce sinistre n'est pas lié à une souscription de votre courtier.",
            )


@router.get("/sinistres", response_model=List[SinistreResponse])
async def get_sinistres_for_courtier(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_sinistre_courtier),
):
    """
    Obtenir les sinistres des souscriptions distribuées par le courtier de l'agent.
    Accès en lecture seule.
    """
    courtier_id = _get_courtier_id_for_agent(db, current_user, ('sinistre',))
    if not courtier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun courtier associé à votre compte. Contactez l'administrateur.",
        )

    query = (
        db.query(Sinistre)
        .join(Souscription, Sinistre.souscription_id == Souscription.id)
        .filter(Souscription.courtier_id == courtier_id)
    )
    if statut:
        query = query.filter(Sinistre.statut == statut)

    sinistres = (
        query
        .options(
            selectinload(Sinistre.alerte),
            selectinload(Sinistre.souscription).selectinload(Souscription.produit_assurance),
            selectinload(Sinistre.souscription).selectinload(Souscription.user),
            selectinload(Sinistre.workflow_steps),
        )
        .order_by(Sinistre.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return sinistres


@router.get("/sinistres/{sinistre_id}", response_model=SinistreResponse)
async def get_sinistre_for_courtier(
    sinistre_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_sinistre_courtier),
):
    """
    Obtenir un sinistre par ID (uniquement si lié à une souscription du courtier).
    Accès en lecture seule.
    """
    courtier_id = _get_courtier_id_for_agent(db, current_user, ('sinistre',))
    if not courtier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun courtier associé à votre compte.",
        )

    sinistre = (
        db.query(Sinistre)
        .options(
            selectinload(Sinistre.alerte),
            selectinload(Sinistre.souscription).selectinload(Souscription.produit_assurance),
            selectinload(Sinistre.souscription).selectinload(Souscription.user),
            selectinload(Sinistre.workflow_steps),
        )
        .filter(Sinistre.id == sinistre_id)
        .first()
    )
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé",
        )
    _check_sinistre_scope(sinistre, courtier_id)

    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first() if sinistre.alerte_id else None
    ensure_workflow_steps(db, sinistre, alerte)
    db.commit()
    db.refresh(sinistre)
    return sinistre


@router.get("/sinistres/{sinistre_id}/workflow", response_model=List[SinistreWorkflowStepResponse])
async def get_sinistre_workflow_for_courtier(
    sinistre_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_sinistre_courtier),
):
    """
    Obtenir toutes les étapes du workflow d'un sinistre du courtier.
    Accès en lecture seule.
    """
    courtier_id = _get_courtier_id_for_agent(db, current_user, ('sinistre',))
    if not courtier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun courtier associé à votre compte.",
        )

    sinistre = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé",
        )
    _check_sinistre_scope(sinistre, courtier_id)

    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first() if sinistre.alerte_id else None
    steps, _ = ensure_workflow_steps(db, sinistre, alerte)
    db.commit()
    steps.sort(key=lambda s: s.ordre)
    return steps
