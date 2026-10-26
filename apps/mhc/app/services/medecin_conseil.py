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
        "medecin_conseil_id": getattr(ville, "medecin_conseil_id", None),
        "medecin_conseil": serialize_medecin_conseil(getattr(ville, "medecin_conseil", None)),
        "created_at": ville.created_at,
        "updated_at": ville.updated_at,
    }


# ---------------------------------------------------------------------------
# Périmètre géographique du médecin-conseil (revue des dossiers médicaux)
# ---------------------------------------------------------------------------
def medecin_covered_city_ids(db: Session, medecin_id: int) -> set[int]:
    """Villes dont le médecin-conseil est responsable : affectation directe
    sur la ville + villes des pays dont il est le médecin-conseil."""
    from app.models.destination import DestinationCity

    direct = (
        db.query(DestinationCity.id)
        .filter(DestinationCity.medecin_conseil_id == medecin_id)
        .all()
    )
    via_pays = (
        db.query(DestinationCity.id)
        .join(DestinationCountry, DestinationCity.pays_id == DestinationCountry.id)
        .filter(DestinationCountry.medecin_conseil_id == medecin_id)
        .all()
    )
    return {r[0] for r in direct} | {r[0] for r in via_pays}


def _destination_city(db: Session, projet: Optional[ProjetVoyage]):
    """Ville de destination référencée du projet de voyage (nom insensible à
    la casse, dans le pays déclaré si possible)."""
    from app.models.destination import DestinationCity

    destination = ((projet.destination if projet else "") or "").strip()
    if not destination:
        return None
    query = db.query(DestinationCity).filter(DestinationCity.nom.ilike(destination))
    country_id = getattr(projet, "destination_country_id", None)
    if country_id:
        ville = query.filter(DestinationCity.pays_id == country_id).first()
        if ville is not None:
            return ville
    return query.first()


def medecin_can_review(db: Session, user: User, souscription: Souscription) -> bool:
    """Un médecin référent MH ne voit/ne valide que les dossiers de ses
    villes assignées. Sans aucune affectation, il n'est pas scopé (legacy).
    Les autres rôles médicaux ne sont jamais scopés."""
    role = getattr(user, "role", None)
    if role != Role.MEDECIN_REFERENT_MH:
        return True

    covered = medecin_covered_city_ids(db, user.id)
    if not covered:
        return True  # aucune affectation → pas de filtre

    projet = souscription.projet_voyage
    country_id = getattr(projet, "destination_country_id", None) if projet else None

    ville = _destination_city(db, projet)
    if ville is not None:
        return ville.id in covered

    # Pas de ville trouvée : le pays entier est-il couvert par ce médecin ?
    if country_id:
        pays = db.query(DestinationCountry).filter(DestinationCountry.id == country_id).first()
        if pays is not None and pays.medecin_conseil_id == user.id:
            return True
    return False


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
    # Police active : seuls les médecins-conseils des destinations couvertes
    # sont pertinents (Téléconsultation MyMHC).
    if souscription_id is None and any(
        s.statut == StatutSouscription.ACTIVE for s in souscriptions
    ):
        souscriptions = [s for s in souscriptions if s.statut == StatutSouscription.ACTIVE]

    items: list[dict[str, Any]] = []
    for souscription in souscriptions:
        projet = souscription.projet_voyage
        country = getattr(projet, "destination_country", None) if projet else None
        # Médecin-conseil de la ville de destination en priorité, sinon pays.
        ville = _destination_city(db, projet)
        medecin = (getattr(ville, "medecin_conseil", None) if ville else None) or (
            getattr(country, "medecin_conseil", None) if country else None
        )
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
                "medecin_conseil": serialize_medecin_conseil(medecin),
            }
        )
    return items
