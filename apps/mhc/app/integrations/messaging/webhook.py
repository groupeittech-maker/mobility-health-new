"""Parsing des événements du webhook Meta WhatsApp Business.

Meta envoie des objets entry[].changes[].value contenant :
- `statuses` : accusés (sent / delivered / read / failed) des messages sortants
- `messages` : messages entrants (ouvre la fenêtre de service de 24 h)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def extract_events(payload: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Aplatit le payload Meta en deux listes : statuses et messages entrants."""
    statuses: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []

    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            if (value.get("messaging_product") or "whatsapp") != "whatsapp":
                continue
            statuses.extend(value.get("statuses") or [])
            messages.extend(value.get("messages") or [])

    return {"statuses": statuses, "messages": messages}


def log_events(events: Dict[str, List[Dict[str, Any]]]) -> None:
    """Journalise les statuts de livraison et les messages entrants."""
    for st in events["statuses"]:
        logger.info(
            "[WHATSAPP] statut message %s -> %s : %s",
            st.get("id"),
            st.get("recipient_id"),
            st.get("status"),
        )
        for err in st.get("errors") or []:
            logger.warning("[WHATSAPP] erreur livraison %s : %s", err.get("code"), err.get("title"))

    for msg in events["messages"]:
        logger.info(
            "[WHATSAPP] message entrant de %s (type=%s, id=%s)",
            msg.get("from"),
            msg.get("type"),
            msg.get("id"),
        )
