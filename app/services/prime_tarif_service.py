"""
Service de résolution du tarif de prime selon durée, zone et âge.
Si aucune ligne de tarif ne correspond, on applique le prix et la durée de base du produit.
"""
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.produit_assurance import ProduitAssurance
from app.models.produit_prime_tarif import ProduitPrimeTarif


def resolve_prime_tarif(
    db: Session,
    product_id: int,
    age: Optional[int] = None,
    destination_country_id: Optional[int] = None,
    zone_code: Optional[str] = None,
    duree_jours: Optional[int] = None,
) -> Tuple[Decimal, bool, Optional[int], Optional[int]]:
    """
    Retourne (prix, from_tarif, duree_min_jours, duree_max_jours) pour un produit donné.
    - from_tarif True si un tarif (durée, zone, âge) a été trouvé.
    - duree_min_jours, duree_max_jours : intervalle du tarif trouvé (sinon None).
    """
    product = db.query(ProduitAssurance).filter(
        ProduitAssurance.id == product_id,
        ProduitAssurance.est_actif == True,
    ).first()
    if not product:
        return (Decimal("0"), False, None, None)

    base_prix = product.cout

    query = (
        db.query(ProduitPrimeTarif)
        .filter(ProduitPrimeTarif.produit_assurance_id == product_id)
    )

    # Filtre durée : duree_min_jours <= duree_jours <= duree_max_jours
    if duree_jours is not None:
        query = query.filter(
            ProduitPrimeTarif.duree_min_jours <= duree_jours,
            ProduitPrimeTarif.duree_max_jours >= duree_jours,
        )

    # Filtre zone : destination_country_id ou zone_code (ou tarif sans zone = toute zone)
    if destination_country_id is not None or zone_code is not None:
        from sqlalchemy import or_
        zone_conditions = []
        if destination_country_id is not None:
            zone_conditions.append(ProduitPrimeTarif.destination_country_id == destination_country_id)
        if zone_code is not None:
            zone_conditions.append(ProduitPrimeTarif.zone_code == zone_code)
        # Accepter aussi les tarifs "toute zone" (destination_country_id et zone_code nulls)
        zone_conditions.append(
            (ProduitPrimeTarif.destination_country_id.is_(None)) & (ProduitPrimeTarif.zone_code.is_(None))
        )
        query = query.filter(or_(*zone_conditions))

    # Filtre âge : (age_min is null or age_min <= age) and (age_max is null or age >= age_max)
    if age is not None:
        query = query.filter(
            (ProduitPrimeTarif.age_min.is_(None)) | (ProduitPrimeTarif.age_min <= age),
            (ProduitPrimeTarif.age_max.is_(None)) | (ProduitPrimeTarif.age_max >= age),
        )

    tarifs = (
        query.order_by(
            ProduitPrimeTarif.ordre_priorite.desc(),
            ProduitPrimeTarif.duree_min_jours,
        )
        .all()
    )

    if tarifs:
        t = tarifs[0]
        return (t.prix, True, t.duree_min_jours, t.duree_max_jours)
    return (base_prix, False, None, None)
