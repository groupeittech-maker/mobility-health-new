"""Schémas pour les tarifs de prime (durée, zone, âge)."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class ProduitPrimeTarifBase(BaseModel):
    duree_min_jours: int = Field(..., ge=0)
    duree_max_jours: int = Field(..., ge=0)
    zone_code: Optional[str] = Field(None, max_length=50)
    destination_country_id: Optional[int] = None
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    prix: Decimal = Field(..., ge=0)
    currency: Optional[str] = Field(default="XAF", max_length=10)
    ordre_priorite: int = Field(default=0, ge=0)


class ProduitPrimeTarifUpdate(BaseModel):
    duree_min_jours: Optional[int] = Field(None, ge=0)
    duree_max_jours: Optional[int] = Field(None, ge=0)
    zone_code: Optional[str] = Field(None, max_length=50)
    destination_country_id: Optional[int] = None
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    prix: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    ordre_priorite: Optional[int] = Field(None, ge=0)


class ProduitPrimeTarifResponse(ProduitPrimeTarifBase):
    id: int
    produit_assurance_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
