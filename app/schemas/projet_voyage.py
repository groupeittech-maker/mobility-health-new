from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.core.enums import StatutProjetVoyage, QuestionnaireType


class ProjetVoyageBase(BaseModel):
    titre: str
    description: Optional[str] = None
    destination: str
    destination_country_id: Optional[int] = None
    date_depart: datetime
    date_retour: Optional[datetime] = None
    nombre_participants: int = 1
    statut: StatutProjetVoyage = StatutProjetVoyage.EN_PLANIFICATION
    notes: Optional[str] = None
    budget_estime: Optional[Decimal] = None
    questionnaire_type: QuestionnaireType = QuestionnaireType.LONG


class ProjetVoyageCreate(ProjetVoyageBase):
    user_id: int


class ProjetVoyageUpdate(BaseModel):
    titre: Optional[str] = None
    description: Optional[str] = None
    destination: Optional[str] = None
    destination_country_id: Optional[int] = None
    date_depart: Optional[datetime] = None
    date_retour: Optional[datetime] = None
    nombre_participants: Optional[int] = None
    statut: Optional[StatutProjetVoyage] = None
    notes: Optional[str] = None
    budget_estime: Optional[Decimal] = None
    questionnaire_type: Optional[QuestionnaireType] = None


class ProjetVoyageDocumentResponse(BaseModel):
    id: int
    doc_type: str
    display_name: str
    content_type: Optional[str] = None
    file_size: int
    uploaded_by: Optional[int] = None
    uploaded_at: datetime
    download_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProjetVoyageResponse(ProjetVoyageBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    documents: List[ProjetVoyageDocumentResponse] = []
    
    model_config = ConfigDict(from_attributes=True)
