from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.enums import Role
from app.models.assureur import Assureur
from app.models.courtier import Courtier
from app.models.user import User
from app.schemas.courtier import CourtierCreate, CourtierResponse, CourtierUpdate
from app.services.minio_service import MinioService

router = APIRouter()


def require_admin(current_user=Depends(get_current_user)):
    if getattr(current_user, "role", None) != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required.",
        )
    return current_user


ALLOWED_LOGO_CONTENT_TYPES = {"image/jpeg", "image/png"}
ALLOWED_LOGO_EXTENSIONS = {"jpg", "jpeg", "png"}


def _ensure_assureur(db: Session, assureur_id: int) -> Assureur:
    assureur = db.query(Assureur).filter(Assureur.id == assureur_id).first()
    if not assureur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assureur introuvable",
        )
    return assureur


def _ensure_agent_comptable_courtier(db: Session, agent_id: Optional[int]) -> Optional[User]:
    if agent_id is None:
        return None
    agent = db.query(User).filter(User.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent comptable introuvable")
    if agent.role != Role.AGENT_COMPTABLE_COURTIER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le compte sélectionné n'est pas un agent comptable courtier",
        )
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'agent comptable sélectionné est inactif",
        )
    return agent


@router.get("", response_model=List[CourtierResponse])
async def list_courtiers(
    search: Optional[str] = Query(None),
    assureur_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    query = db.query(Courtier)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(Courtier.nom.ilike(s), Courtier.pays.ilike(s)))
    if assureur_id is not None:
        query = query.filter(Courtier.assureur_id == assureur_id)
    return query.order_by(Courtier.nom.asc()).all()


@router.post("", response_model=CourtierResponse, status_code=status.HTTP_201_CREATED)
async def create_courtier(
    payload: CourtierCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    existing = (
        db.query(Courtier)
        .filter(func.lower(Courtier.nom) == payload.nom.strip().lower())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un courtier avec ce nom existe déjà.",
        )
    _ensure_assureur(db, payload.assureur_id)
    agent = _ensure_agent_comptable_courtier(db, payload.agent_comptable_id)
    row = Courtier(
        nom=payload.nom.strip(),
        pays=payload.pays.strip(),
        logo_url=payload.logo_url,
        adresse=payload.adresse,
        telephone=payload.telephone,
        assureur_id=payload.assureur_id,
        commission_pct=payload.commission_pct,
        agent_comptable_id=agent.id if agent else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{courtier_id}", response_model=CourtierResponse)
async def update_courtier(
    courtier_id: int,
    payload: CourtierUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    row = db.query(Courtier).filter(Courtier.id == courtier_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Courtier introuvable")
    data = payload.model_dump(exclude_unset=True)
    if "nom" in data and data["nom"]:
        duplicate = (
            db.query(Courtier)
            .filter(
                func.lower(Courtier.nom) == data["nom"].strip().lower(),
                Courtier.id != courtier_id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="Un courtier avec ce nom existe déjà.")
        data["nom"] = data["nom"].strip()
    if "pays" in data and data["pays"]:
        data["pays"] = data["pays"].strip()
    if "assureur_id" in data and data["assureur_id"] is not None:
        _ensure_assureur(db, data["assureur_id"])
    if "agent_comptable_id" in data:
        agent = _ensure_agent_comptable_courtier(db, data["agent_comptable_id"])
        data["agent_comptable_id"] = agent.id if agent else None
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{courtier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_courtier(
    courtier_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    row = db.query(Courtier).filter(Courtier.id == courtier_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courtier introuvable")

    # Détacher les souscriptions existantes avant suppression du courtier.
    # SQL direct pour rester compatible avec les environnements où le mapper
    # chargé ne reflète pas encore tous les attributs ORM.
    db.execute(
        text("UPDATE souscriptions SET courtier_id = NULL WHERE courtier_id = :courtier_id"),
        {"courtier_id": courtier_id},
    )
    db.delete(row)
    db.commit()


@router.post(
    "/{courtier_id}/logo",
    response_model=CourtierResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_courtier_logo(
    courtier_id: int,
    file: UploadFile = File(..., description="Fichier image du logo (PNG, JPG, JPEG)"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = db.query(Courtier).filter(Courtier.id == courtier_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courtier introuvable")
    if not file.content_type or file.content_type not in ALLOWED_LOGO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type de fichier non autorisé. Utilisez image/png ou image/jpeg.",
        )
    ext = (file.filename or "").split(".")[-1].lower() if file.filename else "png"
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        ext = "png"
    try:
        body = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de lire le fichier: {e}",
        )
    if not body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le fichier est vide.")
    try:
        logo_key = MinioService.upload_courtier_logo(courtier_id, body, file.content_type, ext)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du stockage du logo: {e}",
        )
    row.logo_url = logo_key
    db.commit()
    db.refresh(row)
    return row

