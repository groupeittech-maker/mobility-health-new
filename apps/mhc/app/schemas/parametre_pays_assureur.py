from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaxePaysAssureurBase(BaseModel):
    nom: str
    taux_pct: Decimal = Field(..., ge=0, le=100)
    actif: bool = True
    ordre_affichage: int = 0


class TaxePaysAssureurCreate(TaxePaysAssureurBase):
    pass


class TaxePaysAssureurUpdate(BaseModel):
    nom: Optional[str] = None
    taux_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    actif: Optional[bool] = None
    ordre_affichage: Optional[int] = None


class TaxePaysAssureurResponse(TaxePaysAssureurBase):
    id: int
    parametre_pays_assureur_id: int

    model_config = ConfigDict(from_attributes=True)


class ParametrePaysAssureurBase(BaseModel):
    pays_assureur: str
    frais_services_pct: Decimal = Field(..., ge=0, le=100)
    cout_police: Decimal = Field(default=Decimal("0"), ge=0)
    reassureur_nom: str = "SCGRÉ"
    reassureur_pct: Decimal = Field(default=Decimal("10"), ge=0, le=100)
    actif: bool = True


class ParametrePaysAssureurCreate(ParametrePaysAssureurBase):
    taxes: Optional[List[TaxePaysAssureurCreate]] = []


class ParametrePaysAssureurUpdate(BaseModel):
    pays_assureur: Optional[str] = None
    frais_services_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    cout_police: Optional[Decimal] = Field(None, ge=0)
    reassureur_nom: Optional[str] = None
    reassureur_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    actif: Optional[bool] = None
    taxes: Optional[List[TaxePaysAssureurCreate]] = None


class ParametrePaysAssureurResponse(ParametrePaysAssureurBase):
    id: int
    taxes: List[TaxePaysAssureurResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ParametrePaysListResponse(BaseModel):
    pays_assureur: str
    frais_services_pct: float
    cout_police: float = 0.0
    reassureur_nom: str = "SCGRÉ"
    reassureur_pct: float = 10.0
    actif: bool
    total_taxes_pct: float
    nombre_taxes: int


class PaysTaxesDetail(BaseModel):
    pays_assureur: str
    frais_services_pct: float
    cout_police: float = 0.0
    taxes: List[TaxePaysAssureurResponse] = []
    total_taxes_pct: float
    prix_multiplicateur: float
