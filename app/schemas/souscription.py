from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.core.enums import StatutSouscription
from app.schemas.produit_assurance import ProduitAssuranceResponse
from app.schemas.projet_voyage import ProjetVoyageResponse
from app.schemas.user import UserResponse


class SouscriptionBase(BaseModel):
    numero_souscription: str
    prix_applique: Decimal
    date_debut: datetime
    date_fin: Optional[datetime] = None
    statut: StatutSouscription = StatutSouscription.EN_ATTENTE
    notes: Optional[str] = None


class SouscriptionCreate(SouscriptionBase):
    user_id: int
    produit_assurance_id: int
    projet_voyage_id: Optional[int] = None


class SouscriptionUpdate(BaseModel):
    numero_souscription: Optional[str] = None
    prix_applique: Optional[Decimal] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    statut: Optional[StatutSouscription] = None
    notes: Optional[str] = None
    produit_assurance_id: Optional[int] = None
    projet_voyage_id: Optional[int] = None


class SouscriptionResponse(SouscriptionBase):
    id: int
    user_id: int
    produit_assurance_id: int
    projet_voyage_id: Optional[int] = None
    produit_assurance: Optional[ProduitAssuranceResponse] = None
    projet_voyage: Optional[ProjetVoyageResponse] = None
    user: Optional[UserResponse] = None
    validation_medicale: Optional[str] = None
    validation_medicale_par: Optional[int] = None
    validation_medicale_date: Optional[datetime] = None
    validation_medicale_notes: Optional[str] = None
    validation_technique: Optional[str] = None
    validation_technique_par: Optional[int] = None
    validation_technique_date: Optional[datetime] = None
    validation_technique_notes: Optional[str] = None
    validation_finale: Optional[str] = None
    validation_finale_par: Optional[int] = None
    validation_finale_date: Optional[datetime] = None
    validation_finale_notes: Optional[str] = None
    demande_resiliation: Optional[str] = None
    demande_resiliation_date: Optional[datetime] = None
    demande_resiliation_notes: Optional[str] = None
    demande_resiliation_par_agent: Optional[int] = None
    demande_resiliation_date_traitement: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v) if v is not None else None},
    )
