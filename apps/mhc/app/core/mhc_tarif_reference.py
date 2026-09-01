"""Référentiel tarifaire MHC (Projet de tarif + Tableau de répartition).

Les grilles existantes (tarification par zone / produit) restent la source opérationnelle
de calcul des primes. Ce module expose les hypothèses documentaires MHC pour consultation
et pour la répartition de la prime nette.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List


TWOPLACES = Decimal("0.01")

# Zones du projet de tarif
TARIF_ZONES = [
    "intra_afrique",
    "rsa_maghreb",
    "exter_afrique",
    "inter_afrique",
    "france_ue",
]

TARIF_ZONE_LABELS = {
    "intra_afrique": "Tarif Intra-Afrique (hors RSA et Maghreb)",
    "rsa_maghreb": "Tarif Spécial RSA et Maghreb",
    "exter_afrique": "Tarif Extérieur-Afrique (Chine, UAE, Turquie, Inde)",
    "inter_afrique": "Tarif Inter-Afrique",
    "france_ue": "Tarif France et U.E.",
}

# Cinq gammes successives du Projet de tarif (prime nette, coût de police, taxe, PNT)
PROJET_TARIF_GRILLES: List[Dict[str, Dict[str, Decimal]]] = [
    {
        "intra_afrique": {"prime_nette": Decimal("6500"), "cout_police": Decimal("0"), "taxe": Decimal("975"), "pnt": Decimal("7475")},
        "rsa_maghreb": {"prime_nette": Decimal("12000"), "cout_police": Decimal("0"), "taxe": Decimal("1800"), "pnt": Decimal("13800")},
        "exter_afrique": {"prime_nette": Decimal("15000"), "cout_police": Decimal("0"), "taxe": Decimal("2250"), "pnt": Decimal("17250")},
        "inter_afrique": {"prime_nette": Decimal("15000"), "cout_police": Decimal("0"), "taxe": Decimal("2250"), "pnt": Decimal("17250")},
        "france_ue": {"prime_nette": Decimal("6500"), "cout_police": Decimal("10000"), "taxe": Decimal("2475"), "pnt": Decimal("18975")},
    },
    {
        "intra_afrique": {"prime_nette": Decimal("10000"), "cout_police": Decimal("0"), "taxe": Decimal("1500"), "pnt": Decimal("11500")},
        "rsa_maghreb": {"prime_nette": Decimal("10000"), "cout_police": Decimal("0"), "taxe": Decimal("1500"), "pnt": Decimal("11500")},
        "exter_afrique": {"prime_nette": Decimal("12000"), "cout_police": Decimal("0"), "taxe": Decimal("1800"), "pnt": Decimal("13800")},
        "inter_afrique": {"prime_nette": Decimal("15000"), "cout_police": Decimal("0"), "taxe": Decimal("2250"), "pnt": Decimal("17250")},
        "france_ue": {"prime_nette": Decimal("10000"), "cout_police": Decimal("10000"), "taxe": Decimal("3000"), "pnt": Decimal("23000")},
    },
    {
        "intra_afrique": {"prime_nette": Decimal("10000"), "cout_police": Decimal("5000"), "taxe": Decimal("2250"), "pnt": Decimal("17250")},
        "rsa_maghreb": {"prime_nette": Decimal("12500"), "cout_police": Decimal("5000"), "taxe": Decimal("2625"), "pnt": Decimal("20125")},
        "exter_afrique": {"prime_nette": Decimal("15000"), "cout_police": Decimal("5000"), "taxe": Decimal("3000"), "pnt": Decimal("23000")},
        "inter_afrique": {"prime_nette": Decimal("17500"), "cout_police": Decimal("5000"), "taxe": Decimal("3375"), "pnt": Decimal("25875")},
        "france_ue": {"prime_nette": Decimal("13099"), "cout_police": Decimal("10000"), "taxe": Decimal("3464.85"), "pnt": Decimal("26563.85")},
    },
    {
        "intra_afrique": {"prime_nette": Decimal("12500"), "cout_police": Decimal("5000"), "taxe": Decimal("2625"), "pnt": Decimal("20125")},
        "rsa_maghreb": {"prime_nette": Decimal("15000"), "cout_police": Decimal("5000"), "taxe": Decimal("3000"), "pnt": Decimal("23000")},
        "exter_afrique": {"prime_nette": Decimal("17500"), "cout_police": Decimal("5000"), "taxe": Decimal("3375"), "pnt": Decimal("25875")},
        "inter_afrique": {"prime_nette": Decimal("20000"), "cout_police": Decimal("5000"), "taxe": Decimal("3750"), "pnt": Decimal("28750")},
        "france_ue": {"prime_nette": Decimal("20813"), "cout_police": Decimal("10000"), "taxe": Decimal("4621.95"), "pnt": Decimal("35434.95")},
    },
    {
        "intra_afrique": {"prime_nette": Decimal("15000"), "cout_police": Decimal("5000"), "taxe": Decimal("3000"), "pnt": Decimal("23000")},
        "rsa_maghreb": {"prime_nette": Decimal("15000"), "cout_police": Decimal("5000"), "taxe": Decimal("3000"), "pnt": Decimal("23000")},
        "exter_afrique": {"prime_nette": Decimal("17500"), "cout_police": Decimal("5000"), "taxe": Decimal("3375"), "pnt": Decimal("25875")},
        "inter_afrique": {"prime_nette": Decimal("20000"), "cout_police": Decimal("5000"), "taxe": Decimal("3750"), "pnt": Decimal("28750")},
        "france_ue": {"prime_nette": Decimal("24663"), "cout_police": Decimal("10000"), "taxe": Decimal("5199.45"), "pnt": Decimal("39862.45")},
    },
]


def _q(value: Decimal) -> Decimal:
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def split_prime_nette(prime_nette: Decimal, assureur_participation_pct: Decimal = Decimal("20")) -> Dict[str, Decimal]:
    """Répartition documentaire de la prime nette.

    Hypothèse 20 % : assureur 20 %, SCGRE 10 %, MHC 70 %, taxe 15 %.
    Hypothèse 0 % : commission courtier 10 %, SCGRE 10 % du reliquat, MHC 90 % du reliquat, taxe 15 %.
    """
    pn = _q(prime_nette)
    taxe = _q(pn * Decimal("0.15"))
    participation = Decimal(assureur_participation_pct)
    if participation > 0:
        part_assureur = _q(pn * participation / Decimal("100"))
        commission = Decimal("0.00")
        scgre = _q(pn * Decimal("0.10"))
        mhc = _q(pn - part_assureur - scgre)
        hypothese = "assureur_20"
    else:
        part_assureur = Decimal("0.00")
        commission = _q(pn * Decimal("0.10"))
        reliquat = pn - commission
        scgre = _q(reliquat * Decimal("0.10"))
        mhc = _q(reliquat - scgre)
        hypothese = "assureur_0"
    return {
        "hypothese": hypothese,
        "prime_nette": pn,
        "part_assureur": part_assureur,
        "commission": commission,
        "part_scgre": scgre,
        "part_mhc": mhc,
        "taxe": taxe,
        "prime_nette_totale": _q(pn + taxe),
    }


def projet_tarif_public() -> List[dict]:
    result = []
    for index, grille in enumerate(PROJET_TARIF_GRILLES, start=1):
        zones = {}
        for zone_key, amounts in grille.items():
            zones[zone_key] = {
                "libelle": TARIF_ZONE_LABELS[zone_key],
                "prime_nette": str(amounts["prime_nette"]),
                "cout_police": str(amounts["cout_police"]),
                "taxe": str(amounts["taxe"]),
                "pnt": str(amounts["pnt"]),
            }
        result.append({"gamme": index, "zones": zones})
    return result
