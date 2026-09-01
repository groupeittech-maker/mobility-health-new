from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class HospitalExamTarifBase(BaseModel):
    nom: str = Field(..., min_length=1, max_length=200)
    montant: Decimal = Field(..., gt=0)


class HospitalExamTarifCreate(HospitalExamTarifBase):
    pass


class HospitalExamTarifUpdate(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=200)
    montant: Optional[Decimal] = Field(default=None, gt=0)


class HospitalExamTarifResponse(HospitalExamTarifBase):
    id: int
    hospital_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

















