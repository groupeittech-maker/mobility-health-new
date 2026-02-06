from datetime import datetime
from typing import Optional, Dict, List, Any
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, computed_field
from app.core.enums import CleRepartition
from app.schemas.assureur import AssureurSummaryForProduct


class ProduitAssuranceBase(BaseModel):
    # 1. Informations générales
    code: str
    nom: str  # Nom du produit
    description: Optional[str] = None
    version: Optional[str] = None
    est_actif: bool = Field(default=True)  # Statut actif/inactif
    assureur: Optional[str] = None  # Nom de l'assureur
    assureur_id: Optional[int] = None
    image_url: Optional[str] = None  # URL de l'image/miniature du produit
    
    # Coût et répartition
    cout: Decimal  # Coût de base du produit
    currency: Optional[str] = Field(default="XAF")  # Devise (XAF pour franc CFA d'Afrique centrale)
    cle_repartition: CleRepartition = CleRepartition.FIXE
    # Pourcentage de commission reversé à l'assureur (paramétré à la création, dépend du produit et du type de transaction)
    commission_assureur_pct: Optional[Decimal] = Field(default=30, ge=0, le=100)
    
    # 2. Zone géographique couverte (JSON)
    zones_geographiques: Optional[Dict[str, Any]] = None  # {zones: [], pays_eligibles: [], pays_exclus: [], specificites: []}
    
    # 3. Durée du voyage
    duree_min_jours: Optional[int] = None
    duree_max_jours: Optional[int] = None
    duree_validite_jours: Optional[int] = None
    reconduction_possible: bool = False
    couverture_multi_entrees: bool = False
    
    # 4. Profil des assurés
    age_minimum: Optional[int] = None
    age_maximum: Optional[int] = None
    conditions_sante: Optional[str] = None
    categories_assures: Optional[List[str]] = None  # Liste des catégories
    
    # 5. Garanties incluses (JSON structuré)
    garanties: Optional[List[Dict[str, Any]]] = None  # Liste structurée de garanties

    # Primes générées : prime_nette, accessoire, taxes, prime_total
    primes_generees: Optional[Dict[str, Any]] = None
    
    # 6. Exclusions générales (liste de paires clé-valeur, ex: [{"cle": "couleur", "valeur": "verte"}])
    exclusions_generales: Optional[List[Dict[str, Any]]] = None
    
    # Champs legacy (conservés pour compatibilité)
    conditions: Optional[str] = None
    conditions_generales_pdf_url: Optional[str] = None


class ProduitAssuranceCreate(ProduitAssuranceBase):
    pass


class ProduitAssuranceUpdate(BaseModel):
    code: Optional[str] = None
    nom: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    est_actif: Optional[bool] = None
    assureur: Optional[str] = None
    assureur_id: Optional[int] = None
    image_url: Optional[str] = None
    cout: Optional[Decimal] = None
    currency: Optional[str] = None
    cle_repartition: Optional[CleRepartition] = None
    commission_assureur_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    zones_geographiques: Optional[Dict[str, Any]] = None
    duree_min_jours: Optional[int] = None
    duree_max_jours: Optional[int] = None
    duree_validite_jours: Optional[int] = None
    reconduction_possible: Optional[bool] = None
    couverture_multi_entrees: Optional[bool] = None
    age_minimum: Optional[int] = None
    age_maximum: Optional[int] = None
    conditions_sante: Optional[str] = None
    categories_assures: Optional[List[str]] = None
    garanties: Optional[List[Dict[str, Any]]] = None
    primes_generees: Optional[Dict[str, Any]] = None
    exclusions_generales: Optional[List[Dict[str, Any]]] = None
    conditions: Optional[str] = None
    conditions_generales_pdf_url: Optional[str] = None
    raison_modification: Optional[str] = None  # Raison pour le changement de prix


class ProduitQuoteResponse(BaseModel):
    """Devis produit selon durée, zone et âge. Si aucun tarif ne correspond, prix et durée de base."""
    prix: Decimal
    duree_validite_jours: Optional[int] = None
    currency: Optional[str] = "XAF"
    from_tarif: bool = False  # True si un tarif (durée/zone/âge) a été trouvé, sinon prix de base
    # Intervalle du tarif (durée) quand from_tarif True ; sinon None
    duree_min_jours: Optional[int] = None
    duree_max_jours: Optional[int] = None


class ProduitAssuranceResponse(ProduitAssuranceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    assureur_details: Optional[AssureurSummaryForProduct] = None
    
    model_config = ConfigDict(
        from_attributes=True, 
        populate_by_name=True,
        json_encoders={Decimal: lambda v: float(v) if v is not None else None}
    )