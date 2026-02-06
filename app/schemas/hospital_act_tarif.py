from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class HospitalActTarifBase(BaseModel):
    nom: str = Field(..., min_length=1, max_length=200)
    montant: Decimal = Field(..., gt=0)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None


class HospitalActTarifCreate(HospitalActTarifBase):
    pass


class HospitalActTarifUpdate(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=200)
    montant: Optional[Decimal] = Field(default=None, gt=0)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None


class HospitalActTarifResponse(HospitalActTarifBase):
    id: int
    hospital_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


