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
    mode: Literal["stub", "live"] = settings.MESSAGING_SERVICE_MODE  # type: ignore[assignment]
    if mode == "live":
        from app.integrations.messaging.client import MessagingLiveClient

        return MessagingLiveClient(
            base_url=settings.MESSAGING_SERVICE_URL,
            api_key=settings.MESSAGING_SERVICE_API_KEY,
        )
    return MessagingStubClient()
