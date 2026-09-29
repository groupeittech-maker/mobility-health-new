from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DestinationChangeCreate(BaseModel):
    destination_country_id: int
    motif: Optional[str] = None
    billet_document_id: Optional[int] = None


class DestinationChangeDecision(BaseModel):
    approve: bool
    notes: Optional[str] = None


class DestinationChangeResponse(BaseModel):
    id: int
    souscription_id: int
    projet_voyage_id: Optional[int] = None
    user_id: int
    ancienne_destination: Optional[str] = None
    destination_country_id: Optional[int] = None
    destination_country_name: Optional[str] = None
    nouvelle_destination: str
    motif: Optional[str] = None
    billet_document_id: Optional[int] = None
    statut: str
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
