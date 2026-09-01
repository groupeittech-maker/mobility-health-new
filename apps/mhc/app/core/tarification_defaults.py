"""
Surprimes âge par défaut (% additionnels sur la prime de base 18–69 ans),
alignés grille voyage + fiche tarifaire Mobility Health (FCFA).

Si les champs `surprime_*_pct` du produit sont NULL, ces valeurs s’appliquent.
"""
from decimal import Decimal

# % sur tarif de base (même logique que calculateInsurancePremium)
DEFAULT_SURPRIME_MOINS_18_PCT = Decimal("30")
DEFAULT_SURPRIME_70_75_PCT = Decimal("2")
DEFAULT_SURPRIME_76_80_PCT = Decimal("2.5")
DEFAULT_SURPRIME_81_89_PCT = Decimal("4")

# Grille voyage JSON : frais de services = ce % de la prime après surprime âge
FRAIS_SERVICES_SUR_PRIME_PCT = Decimal("15")

# Multiplicateurs pour repli grille SQL (prix réf. × coeff)
DEFAULT_COEFFICIENT_MOINS_18 = Decimal("1.30")
DEFAULT_COEFFICIENT_70_75 = Decimal("1.02")
DEFAULT_COEFFICIENT_76_80 = Decimal("1.025")
DEFAULT_COEFFICIENT_81_89 = Decimal("1.04")

# Libellés lignes matrice primes (admin)
ZONE_ROW_LABELS_FR = {
    "INTRA_AFRIQUE": "Intra-Afrique (hors RSA et Maghreb)",
    "RSA_MAGHREB": "Spécial RSA et Maghreb",
    "EXTRA_AFRIQUE": "Extra-Afrique (Chine, Émirats, Turquie, Inde, …)",
    "INTER_AFRIQUE": "Inter-Afrique",
}

DURATION_BAND_LABELS_FR = {
    "1_7": "1 à 7 jours",
    "8_15": "8 à 15 jours",
    "16_30": "16 à 30 jours",
    "31_60": "31 à 60 jours (2 mois)",
    "61_90": "61 à 90 jours (3 mois)",
}
