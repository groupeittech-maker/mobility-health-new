from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CourtierBase(BaseModel):
    nom: str
    pays: str
    logo_url: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    assureur_id: int
    commission_pct: Decimal = Field(default=0, ge=0, le=100)
    agent_comptable_id: Optional[int] = None


class CourtierCreate(CourtierBase):
    pass


class CourtierUpdate(BaseModel):
    nom: Optional[str] = None
    pays: Optional[str] = None
    logo_url: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    assureur_id: Optional[int] = None
    commission_pct: Optional[Decimal] = Field(default=None, ge=0, le=100)
    agent_comptable_id: Optional[int] = None


class CourtierResponse(CourtierBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

