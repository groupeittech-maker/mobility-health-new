"""Constantes partagées pour la plateforme Mobility Health."""

from decimal import Decimal

HOSPITAL_STAY_ACTS = [
    "Consultation médicale",
    "Stabilisation des fonctions vitales",
    "Pose d'une perfusion",
    "Administration de médicaments",
    "Injection",
    "Immobilisation / plâtre",
    "Suture / pansement",
    "Surveillance post-opératoire",
]

HOSPITAL_STAY_EXAMS = [
    "Analyse sanguine",
    "Analyse urinaire",
    "Radiographie",
    "Scanner",
    "IRM",
    "ECG",
    "Échographie",
    "Test COVID / grippe",
]

# Tarifs par défaut pour la facturation hospitalière.
HOSPITAL_STAY_ACT_PRICES = {
    "Consultation médicale": Decimal("25000"),
    "Stabilisation des fonctions vitales": Decimal("40000"),
    "Pose d'une perfusion": Decimal("18000"),
    "Administration de médicaments": Decimal("15000"),
    "Injection": Decimal("12000"),
    "Immobilisation / plâtre": Decimal("35000"),
    "Suture / pansement": Decimal("22000"),
    "Surveillance post-opératoire": Decimal("30000"),
}

HOSPITAL_STAY_EXAM_PRICES = {
    "Analyse sanguine": Decimal("20000"),
    "Analyse urinaire": Decimal("8000"),
    "Radiographie": Decimal("28000"),
    "Scanner": Decimal("60000"),
    "IRM": Decimal("85000"),
    "ECG": Decimal("18000"),
    "Échographie": Decimal("32000"),
    "Test COVID / grippe": Decimal("15000"),
}

HOSPITAL_STAY_HOURLY_RATE = Decimal("15000")
HOSPITAL_STAY_DEFAULT_ACT_PRICE = Decimal("20000")
HOSPITAL_STAY_DEFAULT_EXAM_PRICE = Decimal("15000")

