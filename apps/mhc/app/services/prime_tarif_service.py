"""
Résolution du tarif :
1) Matrice par produit (produit_prime_tarif) si au moins une ligne existe :
   tarif ligne × (1 + % surprime produit) sauf si la ligne définit une tranche d’âge explicite (tarif final = ligne).
2) Sinon grille voyage JSON : parcours pays de résidence → destination, durée 1–90 j ;
   surprime % sur la prime grille ; frais de services = % de la prime après surprime (tarification_defaults).
3) Sinon grilles SQL (finale, prix × coefficient âge), puis fallback cout × coefficient âge.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.destination import DestinationCountry
from app.models.produit_assurance import ProduitAssurance
from app.models.produit_prime_tarif import ProduitPrimeTarif
from app.models.tarification import (
    TarificationFenetreDuree,
    TarificationGrilleFinale,
    TarificationGrillePrix,
    TarificationTrancheAge,
    TarificationZone,
)
from app.services.voyage_premium_calculator import (
    calculateInsurancePremium,
    duree_tranche,
    resolve_tarification_zone_id_for_destination_country,
    resolve_voyage_tariff_zone_code,
)

if TYPE_CHECKING:
    from app.models.projet_voyage import ProjetVoyage


def _normalize_country_token(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value.lower())
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    normalized = re.sub(r"\s+", "", normalized)
    return normalized.strip()


def _lookup_country_id_by_label(db: Session, raw: Optional[str]) -> Optional[int]:
    """Associe un libellé libre (ex. « Paris, France » ou nom de pays) à destination_countries.id."""
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip()
    pieces = [text]
    if "," in text:
        pieces.extend(p.strip() for p in text.split(",") if p.strip())
    targets: List[str] = []
    for piece in pieces:
        n = _normalize_country_token(piece)
        if n and n not in targets:
            targets.append(n)
    rows = (
        db.query(DestinationCountry)
        .filter(DestinationCountry.est_actif == True)  # noqa: E712
        .all()
    )
    for target in targets:
        for row in rows:
            nom_n = _normalize_country_token(row.nom)
            code_n = _normalize_country_token((row.code or "").strip())
            if target == nom_n or (code_n and target == code_n):
                return row.id
    return None


def _destination_hints_from_projet(projet: ProjetVoyage) -> List[str]:
    hints: List[str] = []
    notes = getattr(projet, "notes", None)
    if notes:
        m = re.search(r"Pays de destination:\s*([^\n]+)", notes, re.IGNORECASE)
        if m:
            hints.append(m.group(1).strip())
    dest = getattr(projet, "destination", None)
    if dest and str(dest).strip():
        hints.append(str(dest).strip())
    return hints


def _residence_hints_from_projet(projet: ProjetVoyage) -> List[str]:
    hints: List[str] = []
    notes = getattr(projet, "notes", None)
    if notes:
        m = re.search(r"Pays de résidence:\s*([^\n]+)", notes, re.IGNORECASE)
        if m:
            hints.append(m.group(1).strip())
    return hints


def resolve_residence_country_id_for_pricing(
    db: Session,
    residence_country_id: Optional[int],
    projet: Optional[ProjetVoyage] = None,
    user_pays_residence: Optional[str] = None,
) -> Optional[int]:
    """Pays de résidence pour la zone tarifaire (parcours résidence → destination)."""
    if residence_country_id is not None:
        return residence_country_id
    if user_pays_residence and str(user_pays_residence).strip():
        cid = _lookup_country_id_by_label(db, user_pays_residence.strip())
        if cid is not None:
            return cid
    if projet is not None:
        for hint in _residence_hints_from_projet(projet):
            cid = _lookup_country_id_by_label(db, hint)
            if cid is not None:
                return cid
    return None


def resolve_destination_country_id_for_pricing(
    db: Session,
    destination_country_id: Optional[int],
    destination_country_name: Optional[str],
    projet: Optional[ProjetVoyage] = None,
) -> Optional[int]:
    """
    Pays effectif pour la tarification : ID requête, puis ID projet, puis nom explicite,
    puis résolution depuis le libellé / notes / destination du projet.
    """
    if destination_country_id is not None:
        return destination_country_id
    if projet is not None and getattr(projet, "destination_country_id", None) is not None:
        return int(projet.destination_country_id)
    if destination_country_name and str(destination_country_name).strip():
        cid = _lookup_country_id_by_label(db, destination_country_name.strip())
        if cid is not None:
            return cid
    if projet is not None:
        for hint in _destination_hints_from_projet(projet):
            cid = _lookup_country_id_by_label(db, hint)
            if cid is not None:
                return cid
    return None


@dataclass
class PrimeTarifDetail:
    prix: Decimal
    from_tarif: bool
    duree_min_jours: Optional[int] = None
    duree_max_jours: Optional[int] = None
    tarif_base: Optional[Decimal] = None  # Prix grille 18–69 avant âge, ou cout produit, ou tarif ligne
    coefficient_zone: Decimal = Decimal("1")
    coefficient_duree: Decimal = Decimal("1")
    coefficient_age: Decimal = Decimal("1")
    moteur_tarifaire: str = "grille"
    pct_surprime_applique: Optional[Decimal] = None  # % sur tarif ligne (matrice produit)
    tarif_ligne_ht_surprime: Optional[Decimal] = None  # Tarif ligne avant % âge produit
    montant_surprime: Optional[Decimal] = None  # Montant absolu (grille voyage JSON, etc.)
    zone_geographique_code: Optional[str] = None
    tranche_duree_code: Optional[str] = None
    frais_services: Optional[Decimal] = None
    prime_assurance: Optional[Decimal] = None  # Prime + surprime (hors frais) ; si None → égal à prix


def _dec(x) -> Decimal:
    if x is None:
        return Decimal("1")
    return Decimal(str(x))


def _row_matches_duration(row: ProduitPrimeTarif, duree_jours: Optional[int]) -> bool:
    if duree_jours is None:
        return True
    return row.duree_min_jours <= duree_jours <= row.duree_max_jours


def _zone_match_tier(
    row: ProduitPrimeTarif,
    destination_country_id: Optional[int],
    zone_code: Optional[str],
) -> int:
    """0 = ne correspond pas ; 3 = pays ; 2 = code zone ; 1 = ligne générique (toutes zones)."""
    if destination_country_id is not None and row.destination_country_id == destination_country_id:
        return 3
    if zone_code and row.zone_code:
        if str(row.zone_code).strip().upper() == str(zone_code).strip().upper():
            return 2
    if row.destination_country_id is None and row.zone_code is None:
        return 1
    return 0


def _row_matches_age(row: ProduitPrimeTarif, age: Optional[int]) -> bool:
    if age is None:
        return True
    if row.age_min is None and row.age_max is None:
        return True
    lo = row.age_min if row.age_min is not None else 0
    hi = row.age_max if row.age_max is not None else 120
    return lo <= age <= hi


def _row_has_explicit_age_band(row: ProduitPrimeTarif) -> bool:
    return row.age_min is not None or row.age_max is not None


def _surprime_pct_produit(product: ProduitAssurance, age: Optional[int]) -> Decimal:
    """% additionnel sur tarif de base (18–69 ans = 0 %).

    Les produits historiques portent souvent `0` en base sur les champs de surprime,
    alors que métier attend les valeurs par défaut (mineur, senior...) tant qu'aucune
    surcharge spécifique n'a été configurée. On considère donc `NULL` et `0` comme
    "non paramétré" pour ces tranches.
    """
    from app.core.tarification_defaults import (
        DEFAULT_SURPRIME_70_75_PCT,
        DEFAULT_SURPRIME_76_80_PCT,
        DEFAULT_SURPRIME_81_89_PCT,
        DEFAULT_SURPRIME_MOINS_18_PCT,
    )

    if age is None:
        return Decimal("0")

    def _pct(attr: str, default: Decimal) -> Decimal:
        v = getattr(product, attr, None)
        if v is not None:
            parsed = Decimal(str(v))
            if parsed > Decimal("0"):
                return parsed
        return default

    if age < 18:
        return _pct("surprime_moins_18_pct", DEFAULT_SURPRIME_MOINS_18_PCT)
    if 70 <= age <= 75:
        return _pct("surprime_70_75_pct", DEFAULT_SURPRIME_70_75_PCT)
    if 76 <= age <= 80:
        return _pct("surprime_76_80_pct", DEFAULT_SURPRIME_76_80_PCT)
    if 81 <= age <= 89:
        return _pct("surprime_81_89_pct", DEFAULT_SURPRIME_81_89_PCT)
    if age >= 90:
        return _pct("surprime_81_89_pct", DEFAULT_SURPRIME_81_89_PCT)
    return Decimal("0")


def _resolve_legacy_prime_tarif(
    db: Session,
    product: ProduitAssurance,
    age: Optional[int],
    destination_country_id: Optional[int],
    zone_code: Optional[str],
    duree_jours: Optional[int],
    base_prix: Decimal,
) -> Optional[PrimeTarifDetail]:
    """
    Matrice produit : zone + durée + (optionnel) tranche d'âge sur la ligne.
    - Ligne sans tranche d'âge (min/max vides) : tarif ligne × (1 + surprime produit %).
    - Ligne avec tranche d'âge : tarif ligne = prime finale (pas de % additionnel produit).
    """
    rows: List[ProduitPrimeTarif] = (
        db.query(ProduitPrimeTarif)
        .filter(ProduitPrimeTarif.produit_assurance_id == product.id)
        .all()
    )
    candidates: List[ProduitPrimeTarif] = []
    for row in rows:
        if not _row_matches_duration(row, duree_jours):
            continue
        zt = _zone_match_tier(row, destination_country_id, zone_code)
        if zt == 0:
            continue
        if not _row_matches_age(row, age):
            continue
        candidates.append(row)

    if not candidates:
        return None

    def sort_key(t: ProduitPrimeTarif) -> Tuple[int, int, int, int]:
        zt = _zone_match_tier(t, destination_country_id, zone_code)
        age_spec = 2 if _row_has_explicit_age_band(t) else 1
        return (zt, age_spec, t.ordre_priorite, t.id)

    candidates.sort(key=sort_key, reverse=True)
    t = candidates[0]
    ligne = _dec(t.prix)
    explicit_age = _row_has_explicit_age_band(t)
    if explicit_age:
        pct = Decimal("0")
        mult = Decimal("1")
    else:
        pct = _surprime_pct_produit(product, age)
        mult = Decimal("1") + (pct / Decimal("100"))
    prix_final = (ligne * mult).quantize(Decimal("0.01"))

    return PrimeTarifDetail(
        prix=prix_final,
        from_tarif=True,
        duree_min_jours=t.duree_min_jours,
        duree_max_jours=t.duree_max_jours,
        tarif_base=ligne,
        coefficient_zone=Decimal("1"),
        coefficient_duree=Decimal("1"),
        coefficient_age=mult,
        moteur_tarifaire="legacy",
        pct_surprime_applique=pct,
        tarif_ligne_ht_surprime=ligne,
        prime_assurance=prix_final,
        frais_services=None,
    )


def _resolve_zone_id(
    db: Session,
    destination_country_id: Optional[int],
    zone_code: Optional[str],
) -> Optional[int]:
    if destination_country_id is not None:
        zid = resolve_tarification_zone_id_for_destination_country(
            db, destination_country_id
        )
        if zid is not None:
            return zid
    if zone_code:
        code = str(zone_code).strip().upper()
        z = (
            db.query(TarificationZone)
            .filter(
                TarificationZone.code == code,
                TarificationZone.est_actif == True,  # noqa: E712
            )
            .first()
        )
        if z:
            return z.id
    return None


def _resolve_fenetre_for_duration(
    db: Session,
    duree_jours: Optional[int],
) -> Optional[TarificationFenetreDuree]:
    if duree_jours is None:
        return None
    rows = (
        db.query(TarificationFenetreDuree)
        .filter(
            TarificationFenetreDuree.est_actif == True,  # noqa: E712
            TarificationFenetreDuree.duree_min_jours <= duree_jours,
            TarificationFenetreDuree.duree_max_jours >= duree_jours,
        )
        .order_by(
            TarificationFenetreDuree.ordre_priorite.desc(),
            TarificationFenetreDuree.duree_min_jours,
        )
        .all()
    )
    return rows[0] if rows else None


def _grille_prix_lookup(
    db: Session,
    zone_id: int,
    fenetre_duree_id: int,
) -> Optional[Decimal]:
    cell = (
        db.query(TarificationGrillePrix)
        .filter(
            TarificationGrillePrix.zone_id == zone_id,
            TarificationGrillePrix.fenetre_duree_id == fenetre_duree_id,
        )
        .first()
    )
    if not cell:
        return None
    return _dec(cell.prix)


def _tranche_age_row_for_age(
    db: Session, age: Optional[int]
) -> Optional[TarificationTrancheAge]:
    """Première tranche active correspondant à l’âge (même ordre que l’ancien _coefficient_age)."""
    if age is None:
        return None
    rows = (
        db.query(TarificationTrancheAge)
        .filter(TarificationTrancheAge.est_actif == True)  # noqa: E712
        .order_by(
            TarificationTrancheAge.ordre_priorite.desc(),
            TarificationTrancheAge.id,
        )
        .all()
    )
    for row in rows:
        ok_min = row.age_min is None or row.age_min <= age
        ok_max = row.age_max is None or row.age_max >= age
        if ok_min and ok_max:
            return row
    return None


def _grille_finale_lookup(
    db: Session,
    product_id: int,
    zone_id: int,
    fenetre_duree_id: int,
    tranche_age_id: int,
) -> Optional[TarificationGrilleFinale]:
    """Ligne produit prioritaire sur ligne globale (produit_assurance_id NULL)."""
    rows = (
        db.query(TarificationGrilleFinale)
        .filter(
            TarificationGrilleFinale.zone_id == zone_id,
            TarificationGrilleFinale.fenetre_duree_id == fenetre_duree_id,
            TarificationGrilleFinale.tranche_age_id == tranche_age_id,
            or_(
                TarificationGrilleFinale.produit_assurance_id == product_id,
                TarificationGrilleFinale.produit_assurance_id.is_(None),
            ),
        )
        .order_by(TarificationGrilleFinale.produit_assurance_id.is_(None).asc())
        .all()
    )
    return rows[0] if rows else None


def _coefficient_age(db: Session, age: Optional[int]) -> Decimal:
    """
    Multiplicateur surprime âge sur le prix grille (référence 18–69 = 1).
    Sans ligne SQL : défauts alignés fiche tarifaire (voir tarification_defaults).
    """
    from app.core.tarification_defaults import (
        DEFAULT_COEFFICIENT_70_75,
        DEFAULT_COEFFICIENT_76_80,
        DEFAULT_COEFFICIENT_81_89,
        DEFAULT_COEFFICIENT_MOINS_18,
    )

    if age is None:
        return Decimal("1")
    row = _tranche_age_row_for_age(db, age)
    if row is not None:
        return _dec(row.coefficient)
    if age < 18:
        return DEFAULT_COEFFICIENT_MOINS_18
    if 18 <= age <= 69:
        return Decimal("1")
    if 70 <= age <= 75:
        return DEFAULT_COEFFICIENT_70_75
    if 76 <= age <= 80:
        return DEFAULT_COEFFICIENT_76_80
    if 81 <= age <= 89:
        return DEFAULT_COEFFICIENT_81_89
    if age >= 90:
        return DEFAULT_COEFFICIENT_81_89
    return Decimal("1")


def resolve_prime_tarif_detail(
    db: Session,
    product_id: int,
    age: Optional[int] = None,
    destination_country_id: Optional[int] = None,
    zone_code: Optional[str] = None,
    duree_jours: Optional[int] = None,
    destination_country_name: Optional[str] = None,
    projet: Optional[ProjetVoyage] = None,
    residence_country_id: Optional[int] = None,
    user_pays_residence: Optional[str] = None,
) -> PrimeTarifDetail:
    product = (
        db.query(ProduitAssurance)
        .filter(
            ProduitAssurance.id == product_id,
            ProduitAssurance.est_actif == True,  # noqa: E712
        )
        .first()
    )
    if not product:
        return PrimeTarifDetail(
            prix=Decimal("0"),
            from_tarif=False,
            tarif_base=None,
            moteur_tarifaire="grille",
            prime_assurance=Decimal("0"),
            frais_services=None,
        )

    dcid = resolve_destination_country_id_for_pricing(
        db, destination_country_id, destination_country_name, projet
    )

    base_prix = _dec(product.cout)
    legacy_count = (
        db.query(ProduitPrimeTarif)
        .filter(ProduitPrimeTarif.produit_assurance_id == product_id)
        .count()
    )

    if legacy_count > 0:
        legacy_hit = _resolve_legacy_prime_tarif(
            db,
            product,
            age,
            dcid,
            zone_code,
            duree_jours,
            base_prix,
        )
        if legacy_hit is not None:
            return legacy_hit

    # Grille voyage canonique (JSON) : parcours résidence → destination + durée 1–90 j
    res_cid = resolve_residence_country_id_for_pricing(
        db, residence_country_id, projet, user_pays_residence
    )
    journey_zone = resolve_voyage_tariff_zone_code(db, res_cid, dcid, zone_code)
    if journey_zone and duree_jours is not None and duree_tranche(duree_jours) is not None:
        real_age = age

        def _surprime_from_product(_a: int) -> Decimal:
            if real_age is None:
                return Decimal("0")
            return _surprime_pct_produit(product, real_age)

        nominal_age = real_age if real_age is not None else 35
        voyage_res = calculateInsurancePremium(
            journey_zone,
            duree_jours,
            nominal_age,
            surprime_resolver=_surprime_from_product,
        )
        lo, hi = voyage_res.duree_min_tranche, voyage_res.duree_max_tranche
        pct = voyage_res.pct_surprime
        mult = (Decimal("1") + pct / Decimal("100")) if pct else Decimal("1")
        return PrimeTarifDetail(
            prix=voyage_res.tarif_total,
            from_tarif=True,
            duree_min_jours=lo,
            duree_max_jours=hi,
            tarif_base=voyage_res.tarif_base,
            coefficient_zone=Decimal("1"),
            coefficient_duree=Decimal("1"),
            coefficient_age=mult,
            moteur_tarifaire="voyage_grille_json",
            pct_surprime_applique=pct,
            tarif_ligne_ht_surprime=voyage_res.tarif_base,
            montant_surprime=voyage_res.montant_surprime,
            zone_geographique_code=voyage_res.zone_geographique,
            tranche_duree_code=voyage_res.tranche_duree_code,
            frais_services=voyage_res.frais_services,
            prime_assurance=voyage_res.prime_totale,
        )

    zone_id = _resolve_zone_id(db, dcid, zone_code)
    fenetre = _resolve_fenetre_for_duration(db, duree_jours)
    ca = _coefficient_age(db, age)

    if zone_id is not None and fenetre is not None and age is not None:
        tr_row = _tranche_age_row_for_age(db, age)
        if tr_row is not None:
            cell_finale = _grille_finale_lookup(
                db, product.id, zone_id, fenetre.id, tr_row.id
            )
            if cell_finale is not None:
                prix_gf = _dec(cell_finale.tarif_final).quantize(Decimal("0.01"))
                coeff_ligne = _dec(cell_finale.coefficient_age)
                pct_gf = ((coeff_ligne - Decimal("1")) * Decimal("100")).quantize(
                    Decimal("0.01")
                )
                return PrimeTarifDetail(
                    prix=prix_gf,
                    from_tarif=True,
                    duree_min_jours=fenetre.duree_min_jours,
                    duree_max_jours=fenetre.duree_max_jours,
                    tarif_base=prix_gf,
                    coefficient_zone=Decimal("1"),
                    coefficient_duree=Decimal("1"),
                    coefficient_age=coeff_ligne,
                    moteur_tarifaire="grille_finale",
                    pct_surprime_applique=(
                        pct_gf if coeff_ligne != Decimal("1") else Decimal("0")
                    ),
                    tarif_ligne_ht_surprime=prix_gf,
                    prime_assurance=prix_gf,
                    frais_services=None,
                )

    if zone_id is not None and fenetre is not None:
        prix_grille = _grille_prix_lookup(db, zone_id, fenetre.id)
        if prix_grille is not None:
            prix = (prix_grille * ca).quantize(Decimal("0.01"))
            pct_grille = ((ca - Decimal("1")) * Decimal("100")).quantize(Decimal("0.01"))
            return PrimeTarifDetail(
                prix=prix,
                from_tarif=True,
                duree_min_jours=fenetre.duree_min_jours,
                duree_max_jours=fenetre.duree_max_jours,
                tarif_base=prix_grille,
                coefficient_zone=Decimal("1"),
                coefficient_duree=Decimal("1"),
                coefficient_age=ca,
                moteur_tarifaire="grille",
                pct_surprime_applique=pct_grille if ca != Decimal("1") else Decimal("0"),
                tarif_ligne_ht_surprime=prix_grille,
                prime_assurance=prix,
                frais_services=None,
            )

    prix = (base_prix * ca).quantize(Decimal("0.01"))
    from_tarif = ca != Decimal("1")
    pct_fb = ((ca - Decimal("1")) * Decimal("100")).quantize(Decimal("0.01"))
    return PrimeTarifDetail(
        prix=prix,
        from_tarif=from_tarif,
        duree_min_jours=fenetre.duree_min_jours if fenetre else None,
        duree_max_jours=fenetre.duree_max_jours if fenetre else None,
        tarif_base=base_prix,
        coefficient_zone=Decimal("1"),
        coefficient_duree=Decimal("1"),
        coefficient_age=ca,
        moteur_tarifaire="fallback_produit",
        pct_surprime_applique=pct_fb if ca != Decimal("1") else Decimal("0"),
        tarif_ligne_ht_surprime=base_prix,
        prime_assurance=prix,
        frais_services=None,
    )


def resolve_prime_tarif(
    db: Session,
    product_id: int,
    age: Optional[int] = None,
    destination_country_id: Optional[int] = None,
    zone_code: Optional[str] = None,
    duree_jours: Optional[int] = None,
    destination_country_name: Optional[str] = None,
    projet: Optional[ProjetVoyage] = None,
    residence_country_id: Optional[int] = None,
    user_pays_residence: Optional[str] = None,
) -> Tuple[Decimal, bool, Optional[int], Optional[int]]:
    """
    Retourne (prix, from_tarif, duree_min_jours, duree_max_jours) pour un produit donné.
    """
    d = resolve_prime_tarif_detail(
        db,
        product_id,
        age=age,
        destination_country_id=destination_country_id,
        zone_code=zone_code,
        duree_jours=duree_jours,
        destination_country_name=destination_country_name,
        projet=projet,
        residence_country_id=residence_country_id,
        user_pays_residence=user_pays_residence,
    )
    return (d.prix, d.from_tarif, d.duree_min_jours, d.duree_max_jours)
