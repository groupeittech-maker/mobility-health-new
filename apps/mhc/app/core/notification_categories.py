"""Catégories de notifications MyMHC (workflow V3 §8.2).

Catégories : compte/sécurité, assurance/souscription, documents, remboursements,
assistance médicale. Les notifications de sécurité et d'urgence sont toujours
envoyées ; les autres peuvent être désactivées (elles restent dans l'application).
"""
from __future__ import annotations

CATEGORY_SECURITY = "compte_securite"
CATEGORY_INSURANCE = "assurance"
CATEGORY_DOCUMENTS = "documents"
CATEGORY_REFUNDS = "remboursements"
CATEGORY_ASSISTANCE = "assistance_medicale"
CATEGORY_CLAIMS = "reclamations"

_PREFIXES = (
    (("security", "account", "login", "password", "compte"), CATEGORY_SECURITY),
    (("sos", "sinistre", "assistance", "teleconsult", "hospital"), CATEGORY_ASSISTANCE),
    (("ristourne", "refund", "remboursement"), CATEGORY_REFUNDS),
    (("attestation", "document", "quittance", "avenant_document", "ecard"), CATEGORY_DOCUMENTS),
    (("reclamation",), CATEGORY_CLAIMS),
)

ESSENTIAL_CATEGORIES = {CATEGORY_SECURITY, CATEGORY_ASSISTANCE}


def notification_category(type_notification: str | None) -> str:
    key = (type_notification or "").lower()
    for prefixes, category in _PREFIXES:
        if any(p in key for p in prefixes):
            return category
    return CATEGORY_INSURANCE


def is_essential(type_notification: str | None) -> bool:
    return notification_category(type_notification) in ESSENTIAL_CATEGORIES
