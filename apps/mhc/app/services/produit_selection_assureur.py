"""
Filtrage des produits d'assurance à l'affichage selon le pays rattaché à l'assureur.

- Cas A (INTRA_AFRIQUE, RSA_MAGHREB, EXTRA_AFRIQUE) : assureurs du **pays de résidence** du voyageur.
- Cas B (INTER_AFRIQUE) : assureurs du **pays de destination**.

La zone parcours est celle de `resolve_voyage_tariff_zone_code` (alignée sur la grille voyage).
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Set

from sqlalchemy.orm import Session

from app.models.destination import DestinationCountry
from app.models.produit_assurance import ProduitAssurance
from app.services.destination_reference import _normalize_name
from app.services.prime_tarif_service import (
    resolve_destination_country_id_for_pricing,
    resolve_residence_country_id_for_pricing,
)
from app.services.voyage_premium_calculator import resolve_voyage_tariff_zone_code

# Tarifs « résident » : intra-Afrique, spécial RSA/Maghreb, extra-Afrique
ZONES_ASSUREUR_PAYS_RESIDENCE = frozenset({"INTRA_AFRIQUE", "RSA_MAGHREB", "EXTRA_AFRIQUE"})


def _country_match_keys(db: Session, country_id: Optional[int]) -> Set[str]:
    """Clés normalisées (nom, code ISO) pour un pays référentiel."""
    keys: Set[str] = set()
    if country_id is None:
        return keys
    row = db.query(DestinationCountry).filter(DestinationCountry.id == country_id).first()
    if not row:
        return keys
    for val in (row.nom, row.code):
        if val and str(val).strip():
            k = _normalize_name(str(val).strip())
            if k:
                keys.add(k)
    return keys


def _assureur_pays_matches_keys(assureur_pays: Optional[str], keys: Set[str]) -> bool:
    if not keys:
        return False
    raw = (assureur_pays or "").strip()
    if not raw:
        return False
    ap = _normalize_name(raw)
    if not ap:
        return False
    if ap in keys:
        return True
    for k in keys:
        if len(k) >= 4 and len(ap) >= 4 and (k in ap or ap in k):
            return True
    return False


def filter_produits_par_territoire_assureur(
    db: Session,
    products: Sequence[ProduitAssurance],
    *,
    residence_country_id: Optional[int] = None,
    destination_country_id: Optional[int] = None,
    residence_country_name: Optional[str] = None,
    destination_country_name: Optional[str] = None,
    zone_code: Optional[str] = None,
) -> List[ProduitAssurance]:
    """
    Retourne une sous-liste de `products` dont l'assureur correspond au pays cible.

    Si le parcours (zone tarifaire / pays) ne peut pas être résolu ou qu'aucun produit
    n'a d'assureur rattaché au pays attendu, retourne une liste vide — on n'expose pas
    d'offres non configurées pour le scénario (évite d'afficher tous les produits actifs).
    """
    if not products:
        return list(products)

    res_cid = resolve_residence_country_id_for_pricing(
        db, residence_country_id, None, residence_country_name
    )
    dcid = resolve_destination_country_id_for_pricing(
        db, destination_country_id, destination_country_name, None
    )
    journey_zone = resolve_voyage_tariff_zone_code(db, res_cid, dcid, zone_code)

    if journey_zone is None:
        return []

    if journey_zone == "INTER_AFRIQUE":
        target_country_id = dcid
    elif journey_zone in ZONES_ASSUREUR_PAYS_RESIDENCE:
        target_country_id = res_cid
    else:
        return []

    if target_country_id is None:
        return []

    keys = _country_match_keys(db, target_country_id)
    if not keys:
        return []

    out: List[ProduitAssurance] = []
    for p in products:
        obj = getattr(p, "assureur_obj", None)
        if obj is None or not getattr(obj, "pays", None):
            continue
        if _assureur_pays_matches_keys(obj.pays, keys):
            out.append(p)

    return out
