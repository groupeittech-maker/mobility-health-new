"""Résolution des coordonnées du médecin-conseil par destination de souscription."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import case
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import Role, StatutSouscription
from app.models.destination import DestinationCountry
from app.models.projet_voyage import ProjetVoyage
from app.models.souscription import Souscription
from app.models.user import User

MEDECIN_CONSEIL_ROLES = {Role.MEDECIN_REFERENT_MH, Role.DOCTOR}


def ensure_medecin_conseil(db: Session, medecin_conseil_id: Optional[int]) -> Optional[User]:
    """Valide qu'un utilisateur peut être assigné comme médecin-conseil d'une destination."""
    if not medecin_conseil_id:
        return None
    doctor = db.query(User).filter(User.id == medecin_conseil_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Médecin-conseil introuvable",
        )
    if doctor.role not in MEDECIN_CONSEIL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'utilisateur sélectionné n'est pas un médecin-conseil",
        )
    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le médecin-conseil sélectionné est inactif",
        )
    return doctor


def serialize_medecin_conseil(user: Optional[User]) -> Optional[dict[str, Any]]:
    if not user:
        return None
    nom = (user.full_name or user.username or user.email or "").strip() or None
    telephone = (getattr(user, "telephone", None) or "").strip() or None
    email = (user.email or "").strip() or None
    if not nom and not telephone and not email:
        return None
    return {
        "id": user.id,
        "nom": nom,
        "telephone": telephone,
        "email": email,
    }


def serialize_destination_country(
    pays: DestinationCountry,
    villes: Optional[list] = None,
    include_villes: bool = True,
) -> dict[str, Any]:
    payload = {
        "id": pays.id,
        "code": pays.code,
        "nom": pays.nom,
        "est_actif": pays.est_actif,
        "ordre_affichage": pays.ordre_affichage,
        "notes": pays.notes,
        "medecin_conseil_id": getattr(pays, "medecin_conseil_id", None),
        "medecin_conseil": serialize_medecin_conseil(getattr(pays, "medecin_conseil", None)),
        "created_at": pays.created_at,
        "updated_at": pays.updated_at,
    }
    if include_villes:
        payload["villes"] = villes if villes is not None else []
    return payload


def serialize_city(ville) -> dict[str, Any]:
    return {
        "id": ville.id,
        "pays_id": ville.pays_id,
        "nom": ville.nom,
        "est_actif": ville.est_actif,
        "ordre_affichage": ville.ordre_affichage,
        "notes": ville.notes,
        "created_at": ville.created_at,
        "updated_at": ville.updated_at,
    }


def _destination_label(projet: Optional[ProjetVoyage], country: Optional[DestinationCountry]) -> Optional[str]:
    country_name = country.nom if country else None
    raw = (projet.destination or "").strip() if projet else ""
    if raw and country_name and country_name.lower() not in raw.lower():
        return f"{raw}, {country_name}"
    return raw or country_name


def list_medecin_conseil_for_user(
    db: Session,
    user: User,
    souscription_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Retourne les coordonnées du médecin-conseil liées à la destination de chaque souscription."""
    query = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.projet_voyage).joinedload(ProjetVoyage.destination_country).joinedload(
                DestinationCountry.medecin_conseil
            )
        )
        .filter(Souscription.user_id == user.id)
    )
    if souscription_id is not None:
        query = query.filter(Souscription.id == souscription_id)

    statut_priority = case(
        (Souscription.statut == StatutSouscription.ACTIVE, 0),
        else_=1,
    )
    souscriptions = query.order_by(statut_priority, Souscription.created_at.desc()).all()

    items: list[dict[str, Any]] = []
    for souscription in souscriptions:
        projet = souscription.projet_voyage
        country = getattr(projet, "destination_country", None) if projet else None
        items.append(
            {
                "souscription_id": souscription.id,
                "numero_souscription": souscription.numero_souscription,
                "statut_souscription": (
                    souscription.statut.value
                    if hasattr(souscription.statut, "value")
                    else str(souscription.statut or "")
                ),
                "destination": _destination_label(projet, country),
                "destination_country_id": getattr(projet, "destination_country_id", None) if projet else None,
                "destination_country_name": country.nom if country else None,
                "medecin_conseil": serialize_medecin_conseil(
                    getattr(country, "medecin_conseil", None) if country else None
                ),
            }
        )
    return items
