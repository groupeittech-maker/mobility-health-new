"""
Calcul de prime voyage à partir d'une grille JSON (zone × tranche de durée).

Chaque cellule de la grille donne la **prime** (FCFA). Les **frais de services** =
15 % de la **prime après surprime** (prime grille + montant surprime âge). Si la
surprime augmente la prime, les 15 % sont recalculés sur ce nouveau montant.

Tranches : 1–7, 8–15, 16–30, 31–60, 61–90 jours.
Zones tarifaires (parcours résidence → destination) :
- INTRA_AFRIQUE : résidence intra-Afrique (hors RSA/Maghreb) → destination dans la même zone.
- INTER_AFRIQUE : résidence hors zone intra → destination intra-Afrique ; ou destination zone « inter ».
- RSA_MAGHREB, EXTRA_AFRIQUE : toute résidence → destination dans cette zone.

La surprime âge (hors 18–69 ans par défaut) est paramétrable par résolveur ou
via les champs produit (intégration prime_tarif_service).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple

# --- Grille de base (FCFA) : prime par zone × tranche (frais = 15 % prime après surprime) ---
GRILLE_PRIME: Dict[str, Dict[str, int]] = {
    "INTRA_AFRIQUE": {
        "1_7": 10_000,
        "8_15": 20_547,
        "16_30": 41_666,
        "31_60": 83_332,
        "61_90": 125_000,
    },
    "RSA_MAGHREB": {
        "1_7": 20_000,
        "8_15": 30_821,
        "16_30": 62_500,
        "31_60": 125_000,
        "61_90": 187_500,
    },
    "EXTRA_AFRIQUE": {
        "1_7": 32_000,
        "8_15": 41_095,
        "16_30": 83_333,
        "31_60": 166_666,
        "61_90": 250_000,
    },
    "INTER_AFRIQUE": {
        "1_7": 42_000,
        "8_15": 53_424,
        "16_30": 108_333,
        "31_60": 216_666,
        "61_90": 325_000,
    },
}

# Alias rétrocompat (admin / imports) : uniquement les primes
GRILLE_TARIFAIRE_BASE: Dict[str, Dict[str, int]] = GRILLE_PRIME

# (code_tranche, min_jours, max_jours) — ordre pour résolution
TRANCHES_DUREE: List[Tuple[str, int, int]] = [
    ("1_7", 1, 7),
    ("8_15", 8, 15),
    ("16_30", 16, 30),
    ("31_60", 31, 60),
    ("61_90", 61, 90),
]

ZONES_CANONIQUES: FrozenSet[str] = frozenset(GRILLE_PRIME.keys())

# Si un pays est rattaché à plusieurs zones, ordre de priorité pour la « classe » destination
# (plus petit = prioritaire). INTRA avant INTER : voyages intra→intra restent tarif INTRA.
_CANONICAL_ZONE_PRIORITY: Dict[str, int] = {
    "RSA_MAGHREB": 10,
    "EXTRA_AFRIQUE": 20,
    "INTRA_AFRIQUE": 30,
    "INTER_AFRIQUE": 40,
}


def _pick_canonical_zone_code(codes: FrozenSet[str]) -> Optional[str]:
    valid = [c for c in codes if c in ZONES_CANONIQUES]
    if not valid:
        return None
    return min(valid, key=lambda c: _CANONICAL_ZONE_PRIORITY.get(c, 999))

CANONICAL_ZONE_DESCRIPTIONS_FR: Dict[str, str] = {
    "INTRA_AFRIQUE": "Intra-Afrique : résidence dans la zone (hors RSA/Maghreb) vers destination dans la même zone",
    "RSA_MAGHREB": "Spécial RSA et Maghreb : toute résidence vers un pays RSA/Maghreb",
    "EXTRA_AFRIQUE": "Extra-Afrique : toute résidence vers Chine, Émirats, Turquie, Inde, …",
    "INTER_AFRIQUE": "Inter-Afrique : résidence hors zone intra vers destination intra-Afrique, ou destination zone inter-Afrique",
}

DUREE_MIN_VOYAGE = 1
DUREE_MAX_VOYAGE = 90

SurprimePctResolver = Callable[[int], Decimal]


class VoyagePremiumValidationError(ValueError):
    """Entrées invalides pour le calcul de prime voyage."""

    def __init__(self, message: str, code: str = "validation_error"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class InsurancePremiumResult:
    """Résultat détaillé du calcul de prime."""

    tarif_base: Decimal  # Prime grille avant surprime âge
    frais_services: Decimal
    montant_surprime: Decimal
    tarif_total: Decimal  # prime + surprime + frais
    prime_totale: Decimal  # prime grille + surprime (sans frais)
    pct_surprime: Decimal
    zone_geographique: str
    tranche_duree_code: str
    duree_min_tranche: int
    duree_max_tranche: int
    duree_voyage: int
    age_voyageur: int


def _dec(x) -> Decimal:
    return Decimal(str(x))


def normalize_zone_code(zone: str) -> str:
    if not zone or not str(zone).strip():
        raise VoyagePremiumValidationError("Zone géographique vide.", "zone_vide")
    return str(zone).strip().upper().replace(" ", "_")


def duree_tranche(duree_jours: int) -> Optional[Tuple[str, int, int]]:
    """Retourne (code, min, max) si la durée est couverte, sinon None."""
    if duree_jours < DUREE_MIN_VOYAGE or duree_jours > DUREE_MAX_VOYAGE:
        return None
    for code, lo, hi in TRANCHES_DUREE:
        if lo <= duree_jours <= hi:
            return (code, lo, hi)
    return None


def tarif_prime_grille(zone_normalisee: str, tranche_code: str) -> Decimal:
    zone_p = GRILLE_PRIME.get(zone_normalisee)
    if not zone_p:
        raise VoyagePremiumValidationError(
            f"Zone inconnue : {zone_normalisee}. "
            f"Valeurs acceptées : {', '.join(sorted(ZONES_CANONIQUES))}.",
            "zone_inconnue",
        )
    if tranche_code not in zone_p:
        raise VoyagePremiumValidationError(
            f"Tranche de durée inconnue : {tranche_code}.",
            "tranche_inconnue",
        )
    return _dec(zone_p[tranche_code])


def frais_services_depuis_prime(prime_apres_surprime: Decimal) -> Decimal:
    """15 % de la prime totale (grille + surprime), arrondi à 2 décimales."""
    from app.core.tarification_defaults import FRAIS_SERVICES_SUR_PRIME_PCT

    if prime_apres_surprime < 0:
        raise VoyagePremiumValidationError(
            "La prime après surprime ne peut pas être négative.",
            "prime_negative",
        )
    return (
        prime_apres_surprime * FRAIS_SERVICES_SUR_PRIME_PCT / Decimal("100")
    ).quantize(Decimal("0.01"))


def tarif_base_grille(zone_normalisee: str, tranche_code: str) -> Decimal:
    """Prime grille seule (avant surprime) — compatibilité."""
    return tarif_prime_grille(zone_normalisee, tranche_code)


def default_surprime_pct_resolver(age: int) -> Decimal:
    """Tranches d’âge : valeurs par défaut fiche tarifaire (voir app.core.tarification_defaults)."""
    from app.core.tarification_defaults import (
        DEFAULT_SURPRIME_70_75_PCT,
        DEFAULT_SURPRIME_76_80_PCT,
        DEFAULT_SURPRIME_81_89_PCT,
        DEFAULT_SURPRIME_MOINS_18_PCT,
    )

    if 18 <= age <= 69:
        return Decimal("0")
    if age < 18:
        return DEFAULT_SURPRIME_MOINS_18_PCT
    if 70 <= age <= 75:
        return DEFAULT_SURPRIME_70_75_PCT
    if 76 <= age <= 80:
        return DEFAULT_SURPRIME_76_80_PCT
    if 81 <= age <= 89:
        return DEFAULT_SURPRIME_81_89_PCT
    if age >= 90:
        return DEFAULT_SURPRIME_81_89_PCT
    return Decimal("0")


def surprime_resolver_from_optional_pcts(
    *,
    surprime_moins_18_pct: Optional[Decimal] = None,
    surprime_70_75_pct: Optional[Decimal] = None,
    surprime_76_80_pct: Optional[Decimal] = None,
    surprime_81_89_pct: Optional[Decimal] = None,
    surprime_hors_standard_pct: Optional[Decimal] = None,
) -> SurprimePctResolver:
    """
    Même logique que le produit. Repli : surprime_hors_standard_pct, sinon défauts métier par tranche.
    """
    from app.core.tarification_defaults import (
        DEFAULT_SURPRIME_70_75_PCT,
        DEFAULT_SURPRIME_76_80_PCT,
        DEFAULT_SURPRIME_81_89_PCT,
        DEFAULT_SURPRIME_MOINS_18_PCT,
    )

    def _pick(optional: Optional[Decimal], band_default: Decimal) -> Decimal:
        if optional is not None:
            return optional
        if surprime_hors_standard_pct is not None:
            return surprime_hors_standard_pct
        return band_default

    def resolver(age: int) -> Decimal:
        if 18 <= age <= 69:
            return Decimal("0")
        if age < 18:
            return _pick(surprime_moins_18_pct, DEFAULT_SURPRIME_MOINS_18_PCT)
        if 70 <= age <= 75:
            return _pick(surprime_70_75_pct, DEFAULT_SURPRIME_70_75_PCT)
        if 76 <= age <= 80:
            return _pick(surprime_76_80_pct, DEFAULT_SURPRIME_76_80_PCT)
        if 81 <= age <= 89:
            return _pick(surprime_81_89_pct, DEFAULT_SURPRIME_81_89_PCT)
        if age >= 90:
            return _pick(surprime_81_89_pct, DEFAULT_SURPRIME_81_89_PCT)
        return Decimal("0")

    return resolver


def calculateInsurancePremium(
    zone_geographique: str,
    duree_voyage: int,
    age_voyageur: int,
    *,
    surprime_resolver: Optional[SurprimePctResolver] = None,
) -> InsurancePremiumResult:
    """
    Calcule prime grille, surprime (sur la prime grille), frais (15 % de la prime après
    surprime) et total.

    - zone_geographique : INTRA_AFRIQUE | RSA_MAGHREB | EXTRA_AFRIQUE | INTER_AFRIQUE
    - duree_voyage : 1 à 90 jours
    - age_voyageur : entier raisonnable (0–120)
    - surprime_resolver(age) -> % à appliquer sur la prime de grille (0 = tarif normal)
    """
    z = normalize_zone_code(zone_geographique)
    if z not in ZONES_CANONIQUES:
        raise VoyagePremiumValidationError(
            f"Zone inconnue : {zone_geographique!r}. "
            f"Attendu : {', '.join(sorted(ZONES_CANONIQUES))}.",
            "zone_inconnue",
        )

    if duree_voyage < 0:
        raise VoyagePremiumValidationError(
            "La durée du voyage ne peut pas être négative.",
            "duree_negative",
        )
    if duree_voyage == 0:
        raise VoyagePremiumValidationError(
            "La durée du voyage doit être d'au moins 1 jour.",
            "duree_zero",
        )

    band = duree_tranche(duree_voyage)
    if band is None:
        raise VoyagePremiumValidationError(
            f"Durée {duree_voyage} j hors plage supportée ({DUREE_MIN_VOYAGE}–{DUREE_MAX_VOYAGE} j).",
            "duree_hors_plage",
        )

    tranche_code, dmin, dmax = band

    if age_voyageur < 0:
        raise VoyagePremiumValidationError("Âge invalide (négatif).", "age_negatif")
    if age_voyageur > 120:
        raise VoyagePremiumValidationError(
            "Âge invalide (supérieur à 120).", "age_invalide"
        )

    prime_base = tarif_prime_grille(z, tranche_code)
    resolver = surprime_resolver or default_surprime_pct_resolver
    pct = resolver(age_voyageur)
    if pct < 0:
        raise VoyagePremiumValidationError(
            "Le pourcentage de surprime ne peut pas être négatif.",
            "surprime_negative",
        )

    montant_surprime = (prime_base * (pct / Decimal("100"))).quantize(Decimal("0.01"))
    prime_totale = (prime_base + montant_surprime).quantize(Decimal("0.01"))
    frais = frais_services_depuis_prime(prime_totale)
    total = (prime_totale + frais).quantize(Decimal("0.01"))

    return InsurancePremiumResult(
        tarif_base=prime_base,
        frais_services=frais,
        montant_surprime=montant_surprime,
        tarif_total=total,
        prime_totale=prime_totale,
        pct_surprime=pct.quantize(Decimal("0.01")),
        zone_geographique=z,
        tranche_duree_code=tranche_code,
        duree_min_tranche=dmin,
        duree_max_tranche=dmax,
        duree_voyage=duree_voyage,
        age_voyageur=age_voyageur,
    )


def resolve_canonical_voyage_zone_code(
    db,
    destination_country_id: Optional[int],
    zone_code: Optional[str],
) -> Optional[str]:
    """
    Zone « pays de destination seul » (référentiel tarification_zones).
    Pour le parcours complet résidence → destination, utiliser
    resolve_voyage_tariff_zone_code.
    """
    if zone_code:
        try:
            z = normalize_zone_code(zone_code)
        except VoyagePremiumValidationError:
            return None
        if z in ZONES_CANONIQUES:
            return z

    if destination_country_id is None:
        return None

    from app.models.tarification import TarificationZone, TarificationZonePays

    rows = (
        db.query(TarificationZonePays, TarificationZone)
        .join(TarificationZone, TarificationZone.id == TarificationZonePays.zone_id)
        .filter(
            TarificationZonePays.destination_country_id == destination_country_id,
            TarificationZone.est_actif == True,  # noqa: E712
        )
        .all()
    )
    acc: set[str] = set()
    for _link, row in rows:
        if not row.code:
            continue
        try:
            z = normalize_zone_code(row.code)
        except VoyagePremiumValidationError:
            continue
        if z in ZONES_CANONIQUES:
            acc.add(z)
    return _pick_canonical_zone_code(frozenset(acc))


def resolve_tarification_zone_id_for_destination_country(db, destination_country_id: int) -> Optional[int]:
    """
    `tarification_zones.id` aligné sur la zone canonique retenue pour le pays (grilles SQL).
    """
    from app.models.tarification import TarificationZone, TarificationZonePays

    rows = (
        db.query(TarificationZone.id, TarificationZone.code)
        .join(TarificationZonePays, TarificationZonePays.zone_id == TarificationZone.id)
        .filter(
            TarificationZonePays.destination_country_id == destination_country_id,
            TarificationZone.est_actif == True,  # noqa: E712
        )
        .all()
    )
    pairs: List[Tuple[int, str]] = []
    acc: set[str] = set()
    for zid, code in rows:
        if not code:
            continue
        try:
            c = normalize_zone_code(code)
        except VoyagePremiumValidationError:
            continue
        if c in ZONES_CANONIQUES:
            pairs.append((zid, c))
            acc.add(c)
    canon = _pick_canonical_zone_code(frozenset(acc))
    if not canon:
        return None
    for zid, c in pairs:
        if c == canon:
            return zid
    return None


def resolve_voyage_tariff_zone_code(
    db,
    residence_country_id: Optional[int],
    destination_country_id: Optional[int],
    zone_code: Optional[str],
) -> Optional[str]:
    """
    Code zone pour la grille JSON selon le parcours pays de résidence → pays de destination.

    Priorité à un zone_code explicite canonique. Sinon :
    - destination RSA/Maghreb → RSA_MAGHREB
    - destination Extra-Afrique → EXTRA_AFRIQUE
    - destination zone inter-Afrique (référentiel) → INTER_AFRIQUE
    - destination intra-Afrique : INTRA si résidence aussi intra, sinon INTER (résidence hors zone intra)
    """
    if zone_code:
        try:
            z = normalize_zone_code(zone_code)
        except VoyagePremiumValidationError:
            pass
        else:
            if z in ZONES_CANONIQUES:
                return z

    dest_z = (
        resolve_canonical_voyage_zone_code(db, destination_country_id, None)
        if destination_country_id
        else None
    )
    res_z = (
        resolve_canonical_voyage_zone_code(db, residence_country_id, None)
        if residence_country_id
        else None
    )

    if dest_z == "RSA_MAGHREB":
        return "RSA_MAGHREB"
    if dest_z == "EXTRA_AFRIQUE":
        return "EXTRA_AFRIQUE"
    if dest_z == "INTER_AFRIQUE":
        return "INTER_AFRIQUE"
    if dest_z == "INTRA_AFRIQUE":
        if res_z == "INTRA_AFRIQUE":
            return "INTRA_AFRIQUE"
        return "INTER_AFRIQUE"
    return dest_z
