from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.questionnaire import QuestionnaireResponse
from app.schemas.hospital_stay import HospitalStayResponse


class SinistreBase(BaseModel):
    description: Optional[str] = None
    statut: str = "en_cours"
    notes: Optional[str] = None


class SinistreResponse(SinistreBase):
    id: int
    alerte_id: int
    souscription_id: Optional[int] = None
    hospital_id: Optional[int] = None
    numero_sinistre: Optional[str] = None
    agent_sinistre_id: Optional[int] = None
    medecin_referent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class HospitalInfo(BaseModel):
    id: int
    nom: str
    adresse: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    latitude: Decimal
    longitude: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class PatientInfo(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class PrestationInfo(BaseModel):
    id: int
    code_prestation: str
    libelle: str
    description: Optional[str] = None
    montant_unitaire: Decimal
    quantite: int
    montant_total: Decimal
    date_prestation: datetime
    statut: str
    
    model_config = ConfigDict(from_attributes=True)


class SinistreWorkflowStepResponse(BaseModel):
    step_key: str
    titre: str
    description: Optional[str] = None
    ordre: int
    statut: str
    completed_at: Optional[datetime] = None
    actor_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class SinistreDetailResponse(SinistreResponse):
    """Réponse détaillée avec toutes les informations du sinistre"""
    numero_souscription: Optional[str] = None
    hospital: Optional[HospitalInfo] = None
    prestations: List[PrestationInfo] = []
    agent_sinistre_nom: Optional[str] = None
    medecin_referent_nom: Optional[str] = None
    workflow_steps: List[SinistreWorkflowStepResponse] = []
    medical_questionnaire: Optional[QuestionnaireResponse] = None
    patient: Optional[PatientInfo] = None
    hospital_stay: Optional[HospitalStayResponse] = None


class SinistreVerificationRequest(BaseModel):
    """Payload pour confirmer ou refuser la véracité d'une alerte SOS."""
    approve: bool
    notes: Optional[str] = None
