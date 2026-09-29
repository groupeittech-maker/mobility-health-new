"""Changement de destination en cours de voyage (kit MyMHC).

Le souscripteur demande un changement de destination dans la zone couverte par
sa police, en joignant son billet et un motif. La demande est décidée par
l'Assureur (agent_sinistre_assureur) ou l'admin.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.souscription import Souscription
from app.models.projet_voyage import ProjetVoyage
from app.models.projet_voyage_document import ProjetVoyageDocument
from app.models.destination import DestinationCountry
from app.models.destination_change import DestinationChangeRequest
from app.schemas.destination_change import (
    DestinationChangeCreate,
    DestinationChangeDecision,
    DestinationChangeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

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


def _serialize(db: Session, req: DestinationChangeRequest) -> DestinationChangeResponse:
    resp = DestinationChangeResponse.model_validate(req)
    if req.destination_country_id:
        country = db.query(DestinationCountry).filter(
            DestinationCountry.id == req.destination_country_id
        ).first()
        resp.destination_country_name = country.nom if country else None
    return resp


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _country_in_policy_zone(souscription: Souscription, country: DestinationCountry) -> bool:
    """Vérifie que la destination demandée est dans la zone couverte par la police
    (zones_geographiques.pays_eligibles / pays_exclus du produit).
    Si le produit n'a pas de grille de zone, on accepte (la décision reste humaine)."""
    produit = souscription.produit_assurance
    zones = getattr(produit, "zones_geographiques", None) if produit else None
    if not isinstance(zones, dict):
        return True
    eligibles = {_norm(p) for p in (zones.get("pays_eligibles") or [])}
    exclus = {_norm(p) for p in (zones.get("pays_exclus") or [])}
    if not eligibles and not exclus:
        return True
    keys = {_norm(country.nom), _norm(country.code)}
    if keys & exclus:
        return False
    if eligibles and not (keys & eligibles):
        return False
    return True


@router.post(
    "/subscriptions/{subscription_id}/destination-change",
    response_model=DestinationChangeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_destination_change(
    subscription_id: int,
    body: DestinationChangeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Le souscripteur demande un changement de destination (zone couverte)."""
    sous = _get_souscription(db, subscription_id)
    if not (_is_admin(current_user) or sous.user_id == current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le souscripteur peut demander un changement de destination.",
        )
    statut_val = getattr(sous.statut, "value", sous.statut)
    if str(statut_val or "").lower() != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le changement de destination n'est possible que sur une police active.",
        )

    country = db.query(DestinationCountry).filter(
        DestinationCountry.id == body.destination_country_id
    ).first()
    if not country:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destination inconnue.",
        )

    projet = None
    if sous.projet_voyage_id:
        projet = db.query(ProjetVoyage).filter(
            ProjetVoyage.id == sous.projet_voyage_id
        ).first()
    if projet and projet.destination_country_id == country.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nouvelle destination est identique à la destination actuelle.",
        )

    if not _country_in_policy_zone(sous, country):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cette destination n'est pas couverte par votre police. "
                "Souscrivez une nouvelle assurance pour ce pays."
            ),
        )

    pending = db.query(DestinationChangeRequest).filter(
        DestinationChangeRequest.souscription_id == subscription_id,
        DestinationChangeRequest.statut == "en_attente",
    ).first()
    if pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une demande de changement de destination est déjà en attente.",
        )

    billet = None
    if body.billet_document_id:
        billet = db.query(ProjetVoyageDocument).filter(
            ProjetVoyageDocument.id == body.billet_document_id,
            ProjetVoyageDocument.projet_voyage_id == sous.projet_voyage_id,
        ).first()
        if not billet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Billet justificatif introuvable pour ce voyage.",
            )

    req = DestinationChangeRequest(
        souscription_id=subscription_id,
        projet_voyage_id=sous.projet_voyage_id,
        user_id=current_user.id,
        ancienne_destination=projet.destination if projet else None,
        destination_country_id=country.id,
        nouvelle_destination=country.nom,
        motif=body.motif,
        billet_document_id=billet.id if billet else None,
        statut="en_attente",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    logger.info(
        "Demande changement destination %s créée (souscription %s -> %s)",
        req.id, subscription_id, country.nom,
    )
    return _serialize(db, req)


@router.get(
    "/subscriptions/{subscription_id}/destination-changes",
    response_model=list[DestinationChangeResponse],
)
async def list_subscription_destination_changes(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historique des demandes de changement de destination d'une police."""
    sous = _get_souscription(db, subscription_id)
    if not (
        _is_admin(current_user)
        or _role(current_user) in ASSUREUR_DECISION_ROLES
        or sous.user_id == current_user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé.")
    rows = (
        db.query(DestinationChangeRequest)
        .filter(DestinationChangeRequest.souscription_id == subscription_id)
        .order_by(DestinationChangeRequest.created_at.desc())
        .all()
    )
    return [_serialize(db, r) for r in rows]


@router.get("/destination-changes", response_model=list[DestinationChangeResponse])
async def list_destination_changes(
    statut: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """File de décision pour l'Assureur / l'admin."""
    if not (_is_admin(current_user) or _role(current_user) in ASSUREUR_DECISION_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé.")
    query = db.query(DestinationChangeRequest)
    if statut:
        query = query.filter(DestinationChangeRequest.statut == statut)
    rows = query.order_by(DestinationChangeRequest.created_at.desc()).all()
    return [_serialize(db, r) for r in rows]


@router.post(
    "/destination-changes/{request_id}/decision",
    response_model=DestinationChangeResponse,
)
async def decide_destination_change(
    request_id: int,
    body: DestinationChangeDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """L'Assureur (ou l'admin) approuve ou refuse la demande.

    À l'approbation, la destination du projet de voyage est mise à jour.
    """
    if not (_is_admin(current_user) or _role(current_user) in ASSUREUR_DECISION_ROLES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul l'Assureur peut décider d'un changement de destination.",
        )
    req = db.query(DestinationChangeRequest).filter(
        DestinationChangeRequest.id == request_id
    ).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable.")
    if req.statut != "en_attente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette demande a déjà été traitée.",
        )

    req.statut = "approuvee" if body.approve else "refusee"
    req.decision_note = body.notes
    req.decided_by_id = current_user.id
    req.decided_at = datetime.utcnow()

    if body.approve and req.projet_voyage_id:
        projet = db.query(ProjetVoyage).filter(
            ProjetVoyage.id == req.projet_voyage_id
        ).first()
        if projet:
            projet.destination = req.nouvelle_destination
            projet.destination_country_id = req.destination_country_id
            suffix = f"Changement de destination approuvé : {req.nouvelle_destination}"
            if req.motif:
                suffix += f" (motif : {req.motif})"
            projet.notes = f"{projet.notes}\n{suffix}" if projet.notes else suffix

    db.commit()
    db.refresh(req)
    return _serialize(db, req)
