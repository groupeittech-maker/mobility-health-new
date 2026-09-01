"""
Couche d'intégration vers les services IT-Tech externes (Payment, OCR/HTR, Digital Trust).

MHC consomme des APIs stables ; l'implémentation (stub ou service live) est sélectionnée
via les variables *_SERVICE_MODE dans la configuration.
"""

from app.integrations.payment import get_payment_client
from app.integrations.ocr import get_ocr_client
from app.integrations.trust import get_identity_client, get_trust_client

__all__ = [
    "get_payment_client",
    "get_ocr_client",
    "get_identity_client",
    "get_trust_client",
]
