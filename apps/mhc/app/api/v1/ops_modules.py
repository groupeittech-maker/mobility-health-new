"""Modules annexes : hôtels, hébergements, transport médical, prestations."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.permissions import (
    F_ALERTE_SOS,
    LEVEL_CONSULTATION,
    LEVEL_EDITION,
    has_permission,
)
from app.models.alerte import Alerte
from app.models.alerte_ops import AlerteEvent
from app.models.ops_modules import Hotel, HotelAssignment, TransportMission, TransportProvider
from app.models.sinistre import Sinistre
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def _role_str(u) -> str:
    r = getattr(u, "role", "user")
    return getattr(r, "value", r) or "user"


def _require(u, feature: str, level: str) -> None:
    if not has_permission(_role_str(u), feature, level):
        raise HTTPException(status_code=403, detail=f"Permission « {feature} » requise")


def _actor(u) -> str:
    return getattr(u, "full_name", None) or getattr(u, "username", None) or ""


class HotelPayload(BaseModel):
    nom: str
    adresse: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    categorie: Optional[str] = None
    contact_nom: Optional[str] = None
    est_actif: bool = True


class ProviderPayload(BaseModel):
    nom: str
    type_vehicule: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    contact_nom: Optional[str] = None
    est_actif: bool = True


class AssignmentPayload(BaseModel):
    hotel_id: int
    user_id: Optional[int] = None
    date_arrivee: Optional[str] = None
    date_depart: Optional[str] = None
    nb_nuits: Optional[int] = None
    notes: Optional[str] = None


class MissionPayload(BaseModel):
    provider_id: Optional[int] = None
    type_transport: Optional[str] = None
    depart: Optional[str] = None
    arrivee: Optional[str] = None
    date_mission: Optional[str] = None
    notes: Optional[str] = None


def _hotel_dict(h: Hotel) -> dict:
    return {"id": h.id, "nom": h.nom, "adresse": h.adresse, "ville": h.ville, "pays": h.pays,
            "telephone": h.telephone, "email": h.email, "categorie": h.categorie,
            "contact_nom": h.contact_nom, "est_actif": h.est_actif,
            "latitude": float(h.latitude) if h.latitude is not None else None,
            "longitude": float(h.longitude) if h.longitude is not None else None}


def _provider_dict(p: TransportProvider) -> dict:
    return {"id": p.id, "nom": p.nom, "type_vehicule": p.type_vehicule, "ville": p.ville,
            "pays": p.pays, "telephone": p.telephone, "email": p.email,
            "contact_nom": p.contact_nom, "est_actif": p.est_actif}


# ---------- Hôtels ----------

@router.get("/hotels", response_model=List[dict])
async def list_hotels(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require(current_user, F_ALERTE_SOS, LEVEL_CONSULTATION)
    return [_hotel_dict(h) for h in db.query(Hotel).filter(Hotel.est_actif == True).order_by(Hotel.nom).all()]


@router.post("/hotels", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_hotel(payload: HotelPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require(current_user, F_ALERTE_SOS, LEVEL_EDITION)
    h = Hotel(**payload.model_dump())
    db.add(h)
    db.commit()
    db.refresh(h)
    return _hotel_dict(h)


@router.put("/hotels/{hotel_id}", response_model=dict)
async def update_hotel(hotel_id: int, payload: HotelPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require(current_user, F_ALERTE_SOS, LEVEL_EDITION)
    h = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hôtel introuvable")
    for k, v in payload.model_dump().items():
        setattr(h, k, v)
    db.commit()
    return _hotel_dict(h)


@router.post("/alertes/{alerte_id}/hebergement", status_code=status.HTTP_201_CREATED)
async def assign_hotel(alerte_id: int, payload: AssignmentPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """« Gérer l'hôtel » depuis le détail d'alerte."""
    _require(current_user, F_ALERTE_SOS, LEVEL_EDITION)
    alerte = db.query(Alerte).filter(Alerte.id == alerte_id).first()
    if not alerte:
        raise HTTPException(status_code=404, detail="Alerte introuvable")
    hotel = db.query(Hotel).filter(Hotel.id == payload.hotel_id, Hotel.est_actif == True).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hôtel introuvable")
    from datetime import datetime as _dt
    assign = HotelAssignment(
        alerte_id=alerte_id,
        hotel_id=payload.hotel_id,
        user_id=payload.user_id or alerte.user_id,
        date_arrivee=_dt.fromisoformat(payload.date_arrivee) if payload.date_arrivee else None,
        date_depart=_dt.fromisoformat(payload.date_depart) if payload.date_depart else None,
        nb_nuits=payload.nb_nuits,
        notes=payload.notes,
        created_by_id=current_user.id,
    )
    db.add(assign)
    db.add(AlerteEvent(alerte_id=alerte_id, event_type="hotel",
                     label=f"Hébergement réservé : {hotel.nom}", actor_id=current_user.id, actor_name=_actor(current_user)))
    db.commit()
    return {"id": assign.id, "hotel": hotel.nom, "statut": assign.statut}


@router.get("/alertes/{alerte_id}/hebergement")
async def get_hebergement(alerte_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require(current_user, F_ALERTE_SOS, LEVEL_CONSULTATION)
    rows = db.query(HotelAssignment).filter(HotelAssignment.alerte_id == alerte_id).order_by(HotelAssignment.created_at.desc()).all()
    return [{"id": a.id, "hotel_id": a.hotel_id, "hotel": a.hotel.nom if a.hotel else None,
             "date_arrivee": a.date_arrivee.isoformat() if a.date_arrivee else None,
             "date_depart": a.date_depart.isoformat() if a.date_depart else None,
             "nb_nuits": a.nb_nuits, "statut": a.statut, "notes": a.notes} for a in rows]


# ---------- Transport médical ----------

@router.get("/transport-providers", response_model=List[dict])
async def list_providers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require(current_user, F_ALERTE_SOS, LEVEL_CONSULTATION)
    return [_provider_dict(p) for p in db.query(TransportProvider).filter(TransportProvider.est_actif == True).order_by(TransportProvider.nom).all()]


@router.post("/transport-providers", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_provider(payload: ProviderPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require(current_user, F_ALERTE_SOS, LEVEL_EDITION)
    p = TransportProvider(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _provider_dict(p)


@router.post("/sinistres/{sinistre_id}/transport", status_code=status.HTTP_201_CREATED)
async def create_mission(sinistre_id: int, payload: MissionPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require(current_user, F_ALERTE_SOS, LEVEL_EDITION)
    sinistre = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()
    if not sinistre:
        raise HTTPException(status_code=404, detail="Sinistre introuvable")
    from datetime import datetime as _dt
    m = TransportMission(
        sinistre_id=sinistre_id,
        provider_id=payload.provider_id,
        type_transport=payload.type_transport,
        depart=payload.depart,
        arrivee=payload.arrivee,
        date_mission=_dt.fromisoformat(payload.date_mission) if payload.date_mission else None,
        notes=payload.notes,
        created_by_id=current_user.id,
    )
    db.add(m)
    if sinistre.alerte_id:
        db.add(AlerteEvent(alerte_id=sinistre.alerte_id, event_type="transport",
                           label=f"Transport médical demandé ({payload.type_transport or 'non précisé'})",
                           actor_id=current_user.id, actor_name=_actor(current_user)))
    db.commit()
    return {"id": m.id, "statut": m.statut}


@router.get("/sinistres/{sinistre_id}/transport")
async def list_missions(sinistre_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require(current_user, F_ALERTE_SOS, LEVEL_CONSULTATION)
    rows = db.query(TransportMission).filter(TransportMission.sinistre_id == sinistre_id).order_by(TransportMission.created_at.desc()).all()
    return [{"id": m.id, "provider_id": m.provider_id, "type_transport": m.type_transport,
             "depart": m.depart, "arrivee": m.arrivee, "statut": m.statut,
             "date_mission": m.date_mission.isoformat() if m.date_mission else None,
             "notes": m.notes} for m in rows]
