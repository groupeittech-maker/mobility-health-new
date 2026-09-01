from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class ContactProcheBase(BaseModel):
    nom: str
    prenom: str
    telephone: str
    email: Optional[EmailStr] = None
    relation: Optional[str] = None
    est_contact_urgence: bool = False
    adresse: Optional[str] = None
    pays: Optional[str] = None


class ContactProcheCreate(ContactProcheBase):
    user_id: int


class ContactProcheUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[EmailStr] = None
    relation: Optional[str] = None
    est_contact_urgence: Optional[bool] = None
    adresse: Optional[str] = None
    pays: Optional[str] = None


class ContactProcheResponse(ContactProcheBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
