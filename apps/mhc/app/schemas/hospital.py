from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.hospital_exam_tarif import HospitalExamTarifResponse
from app.schemas.hospital_act_tarif import HospitalActTarifResponse

# Bornes géographiques pour éviter overflow en base (numeric 11,8)
LAT_MIN, LAT_MAX = -90, 90
LON_MIN, LON_MAX = -180, 180


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

    @field_validator("latitude")
    @classmethod
    def latitude_in_range(cls, v: Decimal) -> Decimal:
        if v is None:
            return v
        f = float(v)
        if not (LAT_MIN <= f <= LAT_MAX):
            raise ValueError(f"La latitude doit être entre {LAT_MIN} et {LAT_MAX} (ex. -4.27 pour Brazzaville).")
        return v

    @field_validator("longitude")
    @classmethod
    def longitude_in_range(cls, v: Decimal) -> Decimal:
        if v is None:
            return v
        f = float(v)
        if not (LON_MIN <= f <= LON_MAX):
            raise ValueError(f"La longitude doit être entre {LON_MIN} et {LON_MAX} (ex. 15.27 pour Brazzaville).")
        return v


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

    @field_validator("latitude")
    @classmethod
    def latitude_in_range(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        f = float(v)
        if not (LAT_MIN <= f <= LAT_MAX):
            raise ValueError(f"La latitude doit être entre {LAT_MIN} et {LAT_MAX}.")
        return v

    @field_validator("longitude")
    @classmethod
    def longitude_in_range(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        f = float(v)
        if not (LON_MIN <= f <= LON_MAX):
            raise ValueError(f"La longitude doit être entre {LON_MIN} et {LON_MAX}.")
        return v


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
