from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.hospital_exam_tarif import HospitalExamTarifResponse
from app.schemas.hospital_act_tarif import HospitalActTarifResponse


class HospitalBase(BaseModel):
    nom: str
    adresse: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = None
    code_postal: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    latitude: Decimal
    longitude: Decimal
    est_actif: bool = True
    specialites: Optional[str] = None
    capacite_lits: Optional[int] = None
    notes: Optional[str] = None


class HospitalCreate(HospitalBase):
    medecin_referent_id: Optional[int] = None
    receptionist_ids: List[int] = Field(default_factory=list)
    doctor_ids: List[int] = Field(default_factory=list)
    accountant_ids: List[int] = Field(default_factory=list)


class HospitalUpdate(BaseModel):
    nom: Optional[str] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = None
    code_postal: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    est_actif: Optional[bool] = None
    specialites: Optional[str] = None
    capacite_lits: Optional[int] = None
    notes: Optional[str] = None
    medecin_referent_id: Optional[int] = None
    receptionist_ids: Optional[List[int]] = None
    doctor_ids: Optional[List[int]] = None
    accountant_ids: Optional[List[int]] = None


class HospitalUserSummary(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class HospitalResponse(HospitalBase):
    id: int
    created_at: datetime
    updated_at: datetime
    medecin_referent_id: Optional[int] = None
    medecin_referent: Optional[HospitalUserSummary] = None
    receptionists_count: int = 0
    doctors_count: int = 0
    accountants_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class HospitalDetailResponse(HospitalResponse):
    receptionists: List[HospitalUserSummary] = Field(default_factory=list)
    doctors: List[HospitalUserSummary] = Field(default_factory=list)
    accountants: List[HospitalUserSummary] = Field(default_factory=list)
    exam_tarifs: List[HospitalExamTarifResponse] = Field(default_factory=list)
    act_tarifs: List[HospitalActTarifResponse] = Field(default_factory=list)


class HospitalMapMarker(BaseModel):
    id: int
    nom: str
    latitude: Decimal
    longitude: Decimal
    ville: Optional[str] = None
    pays: Optional[str] = None
    est_actif: bool
    specialites: Optional[str] = None
    adresse: Optional[str] = None
    medecin_referent_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class HospitalReceptionistCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    is_active: bool = True
