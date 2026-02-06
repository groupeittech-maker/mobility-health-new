from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict

from app.schemas.hospital_act_tarif import HospitalActTarifResponse
from app.schemas.hospital_exam_tarif import HospitalExamTarifResponse


class HospitalMedicalCatalogDefaults(BaseModel):
    hourly_rate: Decimal
    default_act_price: Decimal
    default_exam_price: Decimal


class HospitalMedicalCatalogResponse(BaseModel):
    hospital_id: int
    actes: List[HospitalActTarifResponse]
    examens: List[HospitalExamTarifResponse]
    defaults: HospitalMedicalCatalogDefaults

    model_config = ConfigDict(from_attributes=True)


