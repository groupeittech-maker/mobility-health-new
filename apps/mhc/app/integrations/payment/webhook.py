"""Vérification des webhooks sortants AfriPaie.

Format (docs AfriPaie §7bis) :
- En-tête `Afripaie-Signature: t=<horodatage>,v1=<hmac>`
- HMAC-SHA256 sur `<t>.<corps brut>` avec le secret `whsec_…` du endpoint
- Rejeter si l'horodatage a plus de 5 minutes (anti-rejeu)
- Corps : `{ "id": "evt_<resource>_<type>", "type": "payment.succeeded",
  "created_at": "...", "data": <ressource complète> }`
- En-têtes additionnels : `afripaie-event-id`, `afripaie-event-type`
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional

SIGNATURE_HEADER = "afripaie-signature"
EVENT_ID_HEADER = "afripaie-event-id"
EVENT_TYPE_HEADER = "afripaie-event-type"
TOLERANCE_SECONDS = 300  # 5 minutes, comme recommandé par la doc AfriPaie

# Évènements AfriPaie → statuts internes du contrat MHC.
EVENT_STATUS_MAP = {
    "payment.succeeded": "success",
    "payment.failed": "failed",
    "payment.expired": "expired",
}


def verify_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    secret: str,
    *,
    now: Optional[int] = None,
) -> bool:
    """Vérifie la signature `t=<ts>,v1=<hmac>` d'une notification AfriPaie.

    `raw_body` doit être le corps BRUT de la requête : la signature porte sur
    les octets reçus, pas sur un JSON re-sérialisé.
    """
    if not secret or not signature_header:
        return False

    parts = {}
    for pair in signature_header.split(","):
        if "=" in pair:
            k, v = pair.strip().split("=", 1)
            parts[k] = v
    timestamp = parts.get("t")
    received = parts.get("v1")
    if not timestamp or not received:
        return False

    try:
        ts = int(timestamp)
    except ValueError:
        return False

    current = now if now is not None else int(time.time())
    if abs(current - ts) > TOLERANCE_SECONDS:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        f"{ts}.".encode("utf-8") + raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(received, expected)
