"""Contrat du service de messagerie (SMS / WhatsApp — IT-Tech ou Meta Cloud API)."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel


class MessageSendRequest(BaseModel):
    channel: Literal["sms", "whatsapp"]
    to: str
    message: str
    reference: Optional[str] = None
    # WhatsApp Business (Meta) : un template approuvé est OBLIGATOIRE pour
    # initier une conversation hors fenêtre de 24 h.
    template_name: Optional[str] = None
    template_language: Optional[str] = None
    template_params: Optional[List[str]] = None  # valeurs de {{1}}, {{2}}, …


class MessageSendResponse(BaseModel):
    status: Literal["sent", "queued", "failed"] = "sent"
    channel: Literal["sms", "whatsapp"] = "sms"
    message_id: Optional[str] = None
    details: dict = {}
