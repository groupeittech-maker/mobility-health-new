"""Client HTTP du service de messagerie IT-Tech (SMS / WhatsApp)."""
from __future__ import annotations

from app.integrations.base import BaseServiceClient
from app.integrations.messaging.schemas import MessageSendRequest, MessageSendResponse


class MessagingLiveClient(BaseServiceClient):
    service_name = "messaging"

    def send(self, request: MessageSendRequest) -> MessageSendResponse:
        data = self._request("POST", "/v1/messages/send", json=request.model_dump())
        return MessageSendResponse(**data)
