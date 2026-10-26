"""Client WhatsApp Business — Meta Cloud API (Graph API).

Envoi de messages : POST https://graph.facebook.com/{version}/{phone_number_id}/messages
avec Authorization: Bearer <access_token>.

Règles Meta :
- Message « text » libre : uniquement dans la fenêtre de service de 24 h
  (après un message entrant du client).
- Hors fenêtre : template approuvé obligatoire (type=template).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.integrations.base import BaseServiceClient, ExternalServiceError
from app.integrations.messaging.schemas import MessageSendRequest, MessageSendResponse

logger = logging.getLogger(__name__)


def normalize_msisdn(value: str) -> str:
    """Normalise un numéro vers le format attendu par Meta (chiffres, sans '+')."""
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    # Meta attend le format international complet sans '+' — ex. 242061234567
    return digits


class WhatsAppMetaClient(BaseServiceClient):
    """Client d'envoi via la Meta Cloud API (canal whatsapp uniquement)."""

    service_name = "whatsapp-meta"

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        api_version: str = "v20.0",
        timeout: float = 30.0,
    ):
        super().__init__(
            base_url=f"https://graph.facebook.com/{api_version}",
            api_key=access_token,
            timeout=timeout,
        )
        self.phone_number_id = phone_number_id

    def send(self, request: MessageSendRequest) -> MessageSendResponse:
        if request.channel != "whatsapp":
            return MessageSendResponse(
                status="failed",
                channel=request.channel,
                details={
                    "error": "Le client Meta WhatsApp ne gère pas le canal SMS.",
                    "hint": "Utilisez MESSAGING_SERVICE_MODE=live (agrégateur) pour le SMS.",
                },
            )

        to = normalize_msisdn(request.to)
        if not to:
            return MessageSendResponse(
                status="failed",
                channel="whatsapp",
                details={"error": f"Numéro destinataire invalide : {request.to!r}"},
            )

        payload = self.build_payload(request, to)
        try:
            data = self._request("POST", f"/{self.phone_number_id}/messages", json=payload)
        except ExternalServiceError:
            raise

        return self._map_response(data)

    def build_payload(self, request: MessageSendRequest, to: str) -> Dict[str, Any]:
        """Construit le payload Graph API — template si fourni, sinon texte libre."""
        if request.template_name:
            template: Dict[str, Any] = {
                "name": request.template_name,
                "language": {"code": request.template_language or "fr"},
            }
            if request.template_params:
                template["components"] = [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(p)}
                            for p in request.template_params
                        ],
                    }
                ]
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "template",
                "template": template,
            }

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": request.message},
        }

    @staticmethod
    def _map_response(data: Dict[str, Any]) -> MessageSendResponse:
        messages: List[Dict[str, Any]] = data.get("messages") or []
        contacts: List[Dict[str, Any]] = data.get("contacts") or []
        return MessageSendResponse(
            status="sent",
            channel="whatsapp",
            message_id=messages[0].get("id") if messages else None,
            details={
                "wa_id": contacts[0].get("wa_id") if contacts else None,
                "messaging_product": data.get("messaging_product"),
            },
        )
