from datetime import datetime
from typing import Optional, List, Any
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class WorkflowStepSummary(BaseModel):
    """Résumé d'une étape de prise en charge (sinistre)."""
    step_key: str
    titre: str
    ordre: int
    statut: str
    completed_at: Optional[datetime] = None


class AlerteBase(BaseModel):
    latitude: Decimal
    longitude: Decimal
    adresse: Optional[str] = None
    description: Optional[str] = None
    priorite: str = "normale"


class AlerteCreate(AlerteBase):
    souscription_id: Optional[int] = None


class HospitalBasicInfo(BaseModel):
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


class AlerteResponse(AlerteBase):
    id: int
    user_id: int
    souscription_id: Optional[int] = None
    numero_souscription: Optional[str] = None
    numero_alerte: str
    statut: str
    created_at: datetime
    updated_at: datetime
    sinistre_id: Optional[int] = None
    assigned_hospital: Optional[HospitalBasicInfo] = None
    distance_to_hospital_km: Optional[float] = None
    user_full_name: Optional[str] = None
    user_email: Optional[str] = None
    user_telephone: Optional[str] = None
    user_photo_url: Optional[str] = None
    user_date_naissance: Optional[str] = None  # ISO date pour calcul âge assuré
    user_nom_contact_urgence: Optional[str] = None  # Personne à contacter (nom)
    user_contact_urgence: Optional[str] = None  # Personne à contacter (téléphone)
    medecin_referent_nom: Optional[str] = None  # Médecin référent hôpital assigné
    medecin_referent_telephone: Optional[str] = None
    is_validated: bool = False
    is_oriented: bool = False
    workflow_steps: Optional[List[WorkflowStepSummary]] = None  # Étapes de prise en charge (si sinistre)

    model_config = ConfigDict(from_attributes=True)
