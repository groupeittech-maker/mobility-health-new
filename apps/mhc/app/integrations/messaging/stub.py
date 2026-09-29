"""Client messagerie en mode stub : journalise et répond « sent »."""
from __future__ import annotations

import logging
import uuid

from app.integrations.messaging.schemas import MessageSendRequest, MessageSendResponse

logger = logging.getLogger(__name__)


class MessagingStubClient:
    def send(self, request: MessageSendRequest) -> MessageSendResponse:
        logger.info(
            "[MESSAGING STUB] %s -> %s : %s",
            request.channel,
            request.to,
            request.message[:120],
        )
        return MessageSendResponse(
            status="sent",
            channel=request.channel,
            message_id=f"stub-{uuid.uuid4().hex[:12]}",
            details={"message": "Service messagerie non branché — stub actif"},
        )
