"""Service de lecture des paramètres tarifaires par pays d'assureur."""
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.tarification_defaults import FRAIS_SERVICES_SUR_PRIME_PCT
from app.models.parametre_pays_assureur import ParametrePaysAssureur, TaxePaysAssureur


TaxItem = Tuple[str, Decimal]


def normalize_country(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def get_parametre_pays_assureur(
    db: Session, pays_assureur: Optional[str]
) -> Optional[ParametrePaysAssureur]:
    if not pays_assureur:
        return None
    return (
        db.query(ParametrePaysAssureur)
        .filter(
            ParametrePaysAssureur.pays_assureur.ilike(pays_assureur),
            ParametrePaysAssureur.actif == True,  # noqa: E712
        )
        .first()
    )


def get_frais_services_pct(
    db: Session, pays_assureur: Optional[str]
) -> Decimal:
    """Renvoie le % de frais de services pour le pays assureur, ou la constante par défaut."""
    param = get_parametre_pays_assureur(db, pays_assureur)
    if param and param.frais_services_pct is not None:
        return Decimal(str(param.frais_services_pct))
    return FRAIS_SERVICES_SUR_PRIME_PCT


def get_active_taxes(
    db: Session, pays_assureur: Optional[str]
) -> List[TaxePaysAssureur]:
    """Renvoie les taxes actives pour le pays assureur."""
    if not pays_assureur:
        return []
    return (
        db.query(TaxePaysAssureur)
        .join(ParametrePaysAssureur)
        .filter(
            ParametrePaysAssureur.pays_assureur.ilike(pays_assureur),
            ParametrePaysAssureur.actif == True,  # noqa: E712
            TaxePaysAssureur.actif == True,  # noqa: E712
        )
        .order_by(TaxePaysAssureur.ordre_affichage, TaxePaysAssureur.id)
        .all()
    )


def get_pricing_parameters(
    db: Session, pays_assureur: Optional[str]
) -> Tuple[Decimal, List[TaxePaysAssureur]]:
    """Retourne (frais_services_pct, taxes actives)."""
    return get_frais_services_pct(db, pays_assureur), get_active_taxes(db, pays_assureur)
