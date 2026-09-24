"""Administration des réassureurs (création par l'admin MHC / superviseur technique)."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.permissions import (
    F_COMPTES_REASSUREURS,
    LEVEL_CONSULTATION,
    LEVEL_EDITION,
    has_permission,
)
from app.models.reassureur import Reassureur
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class ReassureurBase(BaseModel):
    nom: str
    code: Optional[str] = None
    pays: Optional[str] = None
    ville: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    contact_nom: Optional[str] = None
    est_actif: bool = True
    cession_defaut_pct: Optional[float] = None
    commission_cession_defaut_pct: Optional[float] = None


class ReassureurUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    pays: Optional[str] = None
    ville: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    contact_nom: Optional[str] = None
    est_actif: Optional[bool] = None
    cession_defaut_pct: Optional[float] = None
    commission_cession_defaut_pct: Optional[float] = None


def _role_str(current_user) -> str:
    role = getattr(current_user, "role", "user")
    if hasattr(role, "value"):
        role = role.value
    return str(role or "user")


def require_reassureurs_edition(current_user: User = Depends(get_current_user)) -> User:
    if not has_permission(_role_str(current_user), F_COMPTES_REASSUREURS, LEVEL_EDITION):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gestion des réassureurs non autorisée")
    return current_user


def require_reassureurs_consult(current_user: User = Depends(get_current_user)) -> User:
    if not has_permission(_role_str(current_user), F_COMPTES_REASSUREURS, LEVEL_CONSULTATION):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Consultation des réassureurs non autorisée")
    return current_user


def _to_dict(r: Reassureur) -> dict:
    return {
        "id": r.id,
        "nom": r.nom,
        "code": r.code,
        "pays": r.pays,
        "ville": r.ville,
        "adresse": r.adresse,
        "telephone": r.telephone,
        "email": r.email,
        "contact_nom": r.contact_nom,
        "est_actif": r.est_actif,
        "cession_defaut_pct": float(r.cession_defaut_pct) if r.cession_defaut_pct is not None else None,
        "commission_cession_defaut_pct": float(r.commission_cession_defaut_pct) if r.commission_cession_defaut_pct is not None else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("", response_model=List[dict])
async def list_reassureurs(
    est_actif: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reassureurs_consult),
):
    q = db.query(Reassureur)
    if est_actif is not None:
        q = q.filter(Reassureur.est_actif == est_actif)
    return [_to_dict(r) for r in q.order_by(Reassureur.nom).all()]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_reassureur(
    payload: ReassureurBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reassureurs_edition),
):
    if payload.code:
        exists = db.query(Reassureur).filter(Reassureur.code == payload.code).first()
        if exists:
            raise HTTPException(status_code=400, detail="Ce code réassureur existe déjà")
    r = Reassureur(**payload.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _to_dict(r)


@router.get("/{reassureur_id}", response_model=dict)
async def get_reassureur(
    reassureur_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reassureurs_consult),
):
    r = db.query(Reassureur).filter(Reassureur.id == reassureur_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Réassureur introuvable")
    return _to_dict(r)


@router.put("/{reassureur_id}", response_model=dict)
async def update_reassureur(
    reassureur_id: int,
    payload: ReassureurUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reassureurs_edition),
):
    r = db.query(Reassureur).filter(Reassureur.id == reassureur_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Réassureur introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return _to_dict(r)


@router.delete("/{reassureur_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reassureur(
    reassureur_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reassureurs_edition),
):
    r = db.query(Reassureur).filter(Reassureur.id == reassureur_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Réassureur introuvable")
    # Désactivation plutôt que suppression si des produits sont liés.
    if r.produits:
        r.est_actif = False
        db.commit()
        return None
    db.delete(r)
    db.commit()
    return None
