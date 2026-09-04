"""Pipeline médecin référent — source de vérité (aligné review-dashboard.js getReferentStep)."""
from __future__ import annotations

from typing import Dict, Optional

from app.models.alerte import Alerte
from app.models.sinistre import Sinistre

REFERENT_PIPELINE_STEPS = (
    "sinistre",
    "sinistre_valide",
    "rapport",
    "rapport_valide",
    "facture",
    "facture_valide",
    "resolu",
)


def get_referent_pipeline_step(
    alerte: Optional[Alerte],
    sinistre: Optional[Sinistre] = None,
) -> str:
    """Classifie un dossier pour l'espace médecin référent (web + mobile)."""
    if not alerte:
        return "resolu"

    if not sinistre:
        statut = (alerte.statut or "").lower()
        return "resolu" if statut == "annulee" else "sinistre"

    stay = getattr(sinistre, "hospital_stay", None)
    invoice = getattr(stay, "invoice", None) if stay else None
    stay_status = (stay.status or "").lower() if stay and stay.status else ""
    invoice_statut = (invoice.statut or "").lower() if invoice and invoice.statut else ""

    if invoice_statut in ("validated", "paid"):
        return "resolu"
    if invoice and invoice.validation_medicale == "rejected":
        return "resolu"

    if stay and stay_status == "awaiting_validation":
        return "rapport"

    statut_urgence = ""
    for step in getattr(sinistre, "workflow_steps", None) or []:
        if step.step_key == "verification_urgence":
            statut_urgence = (step.statut or "").lower()
            break

    if not statut_urgence or statut_urgence not in ("completed", "cancelled"):
        return "sinistre"

    if invoice and invoice.validation_medicale == "pending":
        return "facture"
    if invoice and invoice.validation_medicale == "approved":
        return "facture_valide"

    if stay and stay_status == "validated" and (not invoice or invoice.validation_medicale != "pending"):
        return "rapport_valide"

    if statut_urgence == "completed" or (sinistre.numero_sinistre and not statut_urgence):
        return "sinistre_valide"

    return "sinistre_valide"


def count_referent_pipeline_steps(steps: list[str]) -> Dict[str, int]:
    counts = {key: 0 for key in REFERENT_PIPELINE_STEPS}
    for step in steps:
        if step in counts:
            counts[step] += 1
    return counts
