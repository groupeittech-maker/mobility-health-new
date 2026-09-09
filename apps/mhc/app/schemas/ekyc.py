"""Schémas API eKYC côté MHC."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class EkycSessionCreate(BaseModel):
    souscription_id: int | None = None


class EkycSessionResponse(BaseModel):
    session_id: str
    status: str
    verification_url: Optional[str] = None
    expires_at: Optional[str] = None


class EkycWebhookResponse(BaseModel):
    status: str = "accepted"
