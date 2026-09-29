"""Contrat du service de messagerie IT-Tech (SMS / WhatsApp)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class MessageSendRequest(BaseModel):
    channel: Literal["sms", "whatsapp"]
    to: str
    message: str
    reference: Optional[str] = None


class MessageSendResponse(BaseModel):
    status: Literal["sent", "queued", "failed"] = "sent"
    channel: Literal["sms", "whatsapp"] = "sms"
    message_id: Optional[str] = None
    details: dict = {}
