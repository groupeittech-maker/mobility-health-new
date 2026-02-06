from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class QuestionnaireBase(BaseModel):
    type_questionnaire: str = Field(..., pattern="^(short|long|administratif|medical)$")
    reponses: Dict[str, Any]
    notes: Optional[str] = None


class QuestionnaireCreate(QuestionnaireBase):
    souscription_id: int
    version: int = 1


class QuestionnaireUpdate(BaseModel):
    reponses: Optional[Dict[str, Any]] = None
    statut: Optional[str] = None
    notes: Optional[str] = None


class QuestionnaireResponse(QuestionnaireBase):
    id: int
    souscription_id: int
    version: int
    statut: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class QuestionnaireStatusResponse(BaseModel):
    id: int
    type_questionnaire: str
    statut: str
    version: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

