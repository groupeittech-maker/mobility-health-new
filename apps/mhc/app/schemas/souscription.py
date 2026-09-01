from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.core.enums import StatutSouscription
from app.schemas.produit_assurance import ProduitAssuranceResponse
from app.schemas.projet_voyage import ProjetVoyageResponse
from app.schemas.user import UserResponse


class SouscriptionBase(BaseModel):
    numero_souscription: str
    prix_applique: Decimal
    prime_assurance: Optional[Decimal] = None
    frais_services: Optional[Decimal] = None
    date_debut: datetime
    date_fin: Optional[datetime] = None
    statut: StatutSouscription = StatutSouscription.EN_ATTENTE
    notes: Optional[str] = None
    canal_distribution: str = "assureur"
    courtier_id: Optional[int] = None


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
    canal_distribution: Optional[str] = None
    courtier_id: Optional[int] = None


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


class SubscriptionQuotePriceItem(BaseModel):
    """Devis de prime pour un produit (sans créer de souscription)."""

    produit_assurance_id: int
    prix_applique: float
    prime_assurance: Optional[float] = None
    frais_services: Optional[float] = None
    zone_geographique_code: Optional[str] = None
    zone_libelle_fr: Optional[str] = None
    tranche_duree_code: Optional[str] = None
    duree_min_jours: Optional[int] = None
    duree_max_jours: Optional[int] = None


class SurprimeAgeReferenceItem(BaseModel):
    """Référence affichage : % surprime sur la prime (grille voyage), hors champs produit."""

    tranche: str
    pct: float


class SubscriptionQuotePricesRequest(BaseModel):
    projet_voyage_id: int
    produit_assurance_ids: List[int]
    destination_country_id: Optional[int] = None
    destination_country_name: Optional[str] = None
    residence_country_id: Optional[int] = None
    zone_code: Optional[str] = None
    duree_jours: Optional[int] = None
    age: Optional[int] = None


class SubscriptionQuotePricesResponse(BaseModel):
    quotes: List[SubscriptionQuotePriceItem]
    surprimes_age_reference: List[SurprimeAgeReferenceItem] = []
    frais_services_sur_prime_pct: float = 15.0
