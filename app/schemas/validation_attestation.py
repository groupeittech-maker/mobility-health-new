from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ValidationAttestationBase(BaseModel):
    type_validation: str  # 'medecin', 'technique', 'production'
    est_valide: bool = False
    commentaires: Optional[str] = None


class ValidationAttestationCreate(ValidationAttestationBase):
    """Payload envoyé par les reviewers; l'attestation et l'utilisateur sont déduits du contexte"""
    attestation_id: Optional[int] = None


class ValidationAttestationResponse(ValidationAttestationBase):
    id: int
    attestation_id: int
    valide_par_user_id: Optional[int]
    date_validation: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

