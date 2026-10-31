"""Réclamations (workflow MyMHC V3 §8.1) : assuré (Aide) et traitement back-office."""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.permissions import is_internal_backoffice_role
from app.models.reclamation import Reclamation
from app.services import reclamation_service as svc

router = APIRouter()


class ReclamationCreate(BaseModel):
    categorie: str
    objet: str
    description: str
    souscription_id: Optional[int] = None
    personne_concernee: Optional[str] = None
    pieces_jointes: Optional[list[dict[str, Any]]] = None


class MessageBody(BaseModel):
    message: str


class StatusBody(BaseModel):
    statut: str
    message: Optional[str] = None
    complexe: Optional[bool] = None


def _role(user) -> str:
    role = getattr(user, "role", None)
    return str(getattr(role, "value", role) or "user")


def _require_staff(user) -> None:
    if not is_internal_backoffice_role(_role(user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux profils MHC internes.")


def _get(db: Session, reclamation_id: int) -> Reclamation:
    reclamation = db.query(Reclamation).filter(Reclamation.id == reclamation_id).first()
    if not reclamation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réclamation introuvable.")
    return reclamation


def _owned(db: Session, reclamation_id: int, user) -> Reclamation:
    reclamation = _get(db, reclamation_id)
    if reclamation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réclamation introuvable.")
    return reclamation


@router.get("/reclamations/categories")
async def get_categories():
    return {
        "categories": [{"code": k, "libelle": v} for k, v in svc.CATEGORIES.items()],
        "statuts": [{"code": k, "libelle": v} for k, v in svc.STATUTS.items()],
        "urgence_medicale": svc.URGENCE_MESSAGE,
        "delais_jours_ouvres": {
            "premiere_reponse": svc.DELAI_PREMIERE_REPONSE_JOURS,
            "resolution": svc.DELAI_RESOLUTION_JOURS,
            "resolution_complexe": svc.DELAI_RESOLUTION_COMPLEXE_JOURS,
        },
    }


@router.post("/reclamations", status_code=status.HTTP_201_CREATED)
async def create_reclamation(body: ReclamationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    reclamation = svc.create_reclamation(db, current_user, **body.model_dump())
    return svc.serialize(reclamation)


@router.get("/reclamations")
async def list_my_reclamations(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (
        db.query(Reclamation)
        .filter(Reclamation.user_id == current_user.id)
        .order_by(Reclamation.created_at.desc())
        .all()
    )
    # Suppression de l'application 1 mois après la clôture (archive conservée par MHC).
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=31)
    rows = [r for r in rows if not (r.statut == svc.STATUT_CLOTUREE and r.cloturee_at and r.cloturee_at < cutoff)]
    return [svc.serialize(r) for r in rows]


@router.get("/reclamations/admin/list")
async def list_all_reclamations(
    statut: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    query = db.query(Reclamation)
    if statut:
        query = query.filter(Reclamation.statut == statut)
    return [svc.serialize(r, staff=True) for r in query.order_by(Reclamation.created_at.desc()).limit(500).all()]


@router.get("/reclamations/{reclamation_id}")
async def get_reclamation(reclamation_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if is_internal_backoffice_role(_role(current_user)):
        return svc.serialize(_get(db, reclamation_id), staff=True)
    return svc.serialize(_owned(db, reclamation_id, current_user))


@router.post("/reclamations/{reclamation_id}/messages")
async def add_message(reclamation_id: int, body: MessageBody, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    reclamation = svc.add_user_message(db, _owned(db, reclamation_id, current_user), current_user, body.message)
    return svc.serialize(reclamation)


@router.post("/reclamations/{reclamation_id}/contestation", status_code=status.HTTP_201_CREATED)
async def contest_reclamation(reclamation_id: int, body: MessageBody, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    reexamen = svc.contest(db, _owned(db, reclamation_id, current_user), current_user, body.message)
    return svc.serialize(reexamen)


@router.post("/reclamations/{reclamation_id}/statut")
async def change_reclamation_status(reclamation_id: int, body: StatusBody, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _require_staff(current_user)
    reclamation = svc.change_status(
        db, _get(db, reclamation_id), current_user,
        statut=body.statut, message=body.message, complexe=body.complexe,
    )
    return svc.serialize(reclamation, staff=True)
