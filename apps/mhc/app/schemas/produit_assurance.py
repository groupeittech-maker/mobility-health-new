from datetime import datetime
from typing import Optional, Dict, List, Any
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
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

    # Surprimes sur tarif matrice produit (% additionnel). Prime = tarif_ligne × (1 + pct/100) pour les lignes « référence ».
    surprime_moins_18_pct: Optional[Decimal] = Field(default=0, ge=0, le=1000)
    surprime_70_75_pct: Optional[Decimal] = Field(default=0, ge=0, le=1000)
    surprime_76_80_pct: Optional[Decimal] = Field(default=0, ge=0, le=1000)
    surprime_81_89_pct: Optional[Decimal] = Field(default=0, ge=0, le=1000)
    
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
    
    # 6. Exclusions générales (ex. [{"reference": "Exclusion 1", "exclusion": "texte…"}] ; legacy cle/libelle + valeur)
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
    surprime_moins_18_pct: Optional[Decimal] = Field(None, ge=0, le=1000)
    surprime_70_75_pct: Optional[Decimal] = Field(None, ge=0, le=1000)
    surprime_76_80_pct: Optional[Decimal] = Field(None, ge=0, le=1000)
    surprime_81_89_pct: Optional[Decimal] = Field(None, ge=0, le=1000)
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
    """Devis produit selon durée, zone et âge (coefficients ou matrice historique)."""
    prix: Decimal
    duree_validite_jours: Optional[int] = None
    currency: Optional[str] = "XAF"
    from_tarif: bool = False  # True si une règle a modifié le tarif par rapport au seul tarif de base
    duree_min_jours: Optional[int] = None
    duree_max_jours: Optional[int] = None
    tarif_base: Optional[Decimal] = None
    coefficient_zone: Optional[Decimal] = None
    coefficient_duree: Optional[Decimal] = None
    coefficient_age: Optional[Decimal] = None
    moteur_tarifaire: Optional[str] = None  # "grille_finale" | "grille" | "legacy" | "fallback_produit"
    # Matrice produit : % additionnel appliqué sur tarif ligne (0 si ligne à âge explicite ou hors tranche)
    pct_surprime_applique: Optional[Decimal] = None
    tarif_ligne_ht_surprime: Optional[Decimal] = None  # Montant ligne avant surprime
    montant_surprime: Optional[Decimal] = None  # Surprime absolue (ex. grille voyage JSON)
    tarif_total: Optional[Decimal] = None  # Redondant avec prix ; utile pour lecture API explicite
    zone_geographique_code: Optional[str] = None  # Code zone canonique si grille voyage
    tranche_duree_code: Optional[str] = None
    frais_services: Optional[Decimal] = None  # Grille voyage : frais fixes (hors surprime)
    prime_assurance: Optional[Decimal] = None  # Prime + surprime âge (sans frais) ; sinon = prix


class VoyagePremiumCalculateRequest(BaseModel):
    """Calcul autonome de prime (grille JSON), sans produit — surprimes optionnelles."""

    zone_geographique: str = Field(..., min_length=1, max_length=50)
    duree_voyage: int = Field(..., ge=1, le=90)
    age_voyageur: int = Field(..., ge=0, le=120)
    # % sur tarif de base si âge hors tranches ci-dessous (défaut moteur : 20 %)
    surprime_hors_standard_pct: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1000,
        description="Appliqué si l’âge ne tombe dans aucune tranche explicite ci-dessous",
    )
    surprime_moins_18_pct: Optional[Decimal] = Field(None, ge=0, le=1000)
    surprime_70_75_pct: Optional[Decimal] = Field(None, ge=0, le=1000)
    surprime_76_80_pct: Optional[Decimal] = Field(None, ge=0, le=1000)
    surprime_81_89_pct: Optional[Decimal] = Field(None, ge=0, le=1000)


class VoyagePremiumCalculateResponse(BaseModel):
    tarif_base: Decimal
    frais_services: Decimal
    montant_surprime: Decimal
    prime_totale: Decimal
    tarif_total: Decimal
    pct_surprime: Decimal
    zone_geographique: str
    tranche_duree_code: str
    duree_min_tranche: int
    duree_max_tranche: int


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