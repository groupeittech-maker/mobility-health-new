"""Intégration Messagerie — SMS / WhatsApp (canaux de vérification MyMHC)."""
from __future__ import annotations

from typing import Literal, Protocol

from app.core.config import settings
from app.integrations.messaging.schemas import (
    MessageSendRequest,
    MessageSendResponse,
)
from app.integrations.messaging.stub import MessagingStubClient


class MessagingClient(Protocol):
    def send(self, request: MessageSendRequest) -> MessageSendResponse: ...


def get_messaging_client() -> MessagingClient:
    mode: Literal["stub", "live", "meta"] = settings.MESSAGING_SERVICE_MODE  # type: ignore[assignment]
    if mode == "meta":
        from app.integrations.messaging.whatsapp_meta import WhatsAppMetaClient

        return WhatsAppMetaClient(
            access_token=settings.WHATSAPP_ACCESS_TOKEN,
            phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
            api_version=settings.WHATSAPP_API_VERSION,
        )
    if mode == "live":
        from app.integrations.messaging.client import MessagingLiveClient

        return MessagingLiveClient(
            base_url=settings.MESSAGING_SERVICE_URL,
            api_key=settings.MESSAGING_SERVICE_API_KEY,
        )
    return MessagingStubClient()
