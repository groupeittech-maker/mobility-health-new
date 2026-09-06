"""Contrôles d'éligibilité médicale à la souscription."""
from __future__ import annotations

from typing import Any, Mapping

PREGNANCY_MAX_MONTHS = 5
PREGNANCY_INELIGIBLE_MESSAGE = (
    "Vous n'êtes pas éligible pour être assuré par nos services "
    "(grossesse de plus de 5 mois)."
)


class MedicalEligibilityError(ValueError):
    """Réponse médicale incompatible avec une souscription."""


def _first_value(reponses: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in reponses and reponses[key] not in (None, ""):
            return reponses[key]
    return None


def parse_pregnancy_months(reponses: Mapping[str, Any]) -> int | None:
    raw = _first_value(reponses, "moisGrossesse", "mois_grossesse")
    if raw in (None, ""):
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def validate_medical_eligibility(reponses: Mapping[str, Any] | None) -> None:
    """Bloque la souscription si grossesse > 5 mois révolus."""
    if not reponses:
        return
    enceinte = str(
        _first_value(reponses, "enceinte", "pregnancy") or ""
    ).strip().lower()
    if enceinte != "oui":
        return

    months = parse_pregnancy_months(reponses)
    if months is None or months < 1:
        raise MedicalEligibilityError("Veuillez indiquer le nombre de mois de grossesse.")
    if months > PREGNANCY_MAX_MONTHS:
        raise MedicalEligibilityError(PREGNANCY_INELIGIBLE_MESSAGE)
