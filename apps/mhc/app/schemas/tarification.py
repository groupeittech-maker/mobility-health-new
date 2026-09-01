"""Schémas API pour zones, fenêtres de durée et tranches d'âge (coefficients)."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Zones ---
class TarificationZoneBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    nom: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    coefficient: Decimal = Field(default=Decimal("1"), ge=0)
    ordre_affichage: int = Field(default=0, ge=0)
    est_actif: bool = True


class TarificationZoneCreate(TarificationZoneBase):
    pass


class TarificationZoneUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=50)
    nom: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    coefficient: Optional[Decimal] = Field(None, ge=0)
    ordre_affichage: Optional[int] = Field(None, ge=0)
    est_actif: Optional[bool] = None


class TarificationZoneResponse(TarificationZoneBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TarificationZonePaysUpdate(BaseModel):
    """Remplace la liste des pays rattachés à une zone."""

    destination_country_ids: List[int] = Field(default_factory=list)


class TarificationZoneDetailResponse(TarificationZoneResponse):
    destination_country_ids: List[int] = Field(default_factory=list)


# --- Fenêtres durée ---
class TarificationFenetreDureeBase(BaseModel):
    libelle: Optional[str] = Field(None, max_length=200)
    duree_min_jours: int = Field(..., ge=0)
    duree_max_jours: int = Field(..., ge=0)
    coefficient: Decimal = Field(default=Decimal("1"), ge=0)
    ordre_priorite: int = Field(default=0, ge=0)
    est_actif: bool = True


class TarificationFenetreDureeCreate(TarificationFenetreDureeBase):
    pass


class TarificationFenetreDureeUpdate(BaseModel):
    libelle: Optional[str] = None
    duree_min_jours: Optional[int] = Field(None, ge=0)
    duree_max_jours: Optional[int] = Field(None, ge=0)
    coefficient: Optional[Decimal] = Field(None, ge=0)
    ordre_priorite: Optional[int] = Field(None, ge=0)
    est_actif: Optional[bool] = None


class TarificationFenetreDureeResponse(TarificationFenetreDureeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Tranches âge ---
class TarificationTrancheAgeBase(BaseModel):
    libelle: Optional[str] = Field(None, max_length=200)
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    coefficient: Decimal = Field(
        default=Decimal("1"),
        ge=0,
        description="Multiplicateur sur le prix grille (réf. 18–69 ans). Ex. 1,30 = +30 %",
    )
    ordre_priorite: int = Field(default=0, ge=0)
    est_actif: bool = True


class TarificationTrancheAgeCreate(TarificationTrancheAgeBase):
    pass


class TarificationTrancheAgeUpdate(BaseModel):
    libelle: Optional[str] = None
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    coefficient: Optional[Decimal] = Field(None, ge=0)
    ordre_priorite: Optional[int] = Field(None, ge=0)
    est_actif: Optional[bool] = None


class TarificationTrancheAgeResponse(TarificationTrancheAgeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Grille prix (zone × fenêtre) : montant de référence 18–69 ans ---
class TarificationGrillePrixUpsert(BaseModel):
    zone_id: int = Field(..., ge=1)
    fenetre_duree_id: int = Field(..., ge=1)
    prix: Decimal = Field(..., ge=0)


class TarificationGrillePrixCellResponse(BaseModel):
    id: int
    zone_id: int
    fenetre_duree_id: int
    prix: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TarificationGrilleMatrixResponse(BaseModel):
    zones: List[TarificationZoneResponse]
    fenetres: List[TarificationFenetreDureeResponse]
    cellules: List[TarificationGrillePrixCellResponse]


# --- Grille finale (zone × durée × tranche) : tarif affiché au devis ---
class TarificationGrilleFinaleUpsert(BaseModel):
    zone_id: int = Field(..., ge=1)
    fenetre_duree_id: int = Field(..., ge=1)
    tranche_age_id: int = Field(..., ge=1)
    tarif_final: Decimal = Field(..., ge=0)
    coefficient_age: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Si omis, repris du multiplicateur de la tranche d’âge au moment de l’enregistrement",
    )


class TarificationGrilleFinaleRowResponse(BaseModel):
    """Une ligne du tableau final (libellés pour affichage admin)."""

    id: int
    produit_assurance_id: Optional[int] = None
    zone_id: int
    zone_code: str
    zone_nom: str
    fenetre_duree_id: int
    fenetre_libelle: Optional[str] = None
    duree_min_jours: int
    duree_max_jours: int
    tranche_age_id: int
    tranche_libelle: Optional[str] = None
    tranche_age_min: Optional[int] = None
    tranche_age_max: Optional[int] = None
    coefficient_age: Decimal = Field(
        ...,
        description="Coefficient enregistré pour cette ligne (transparence)",
    )
    tarif_final: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TarificationGrilleFinaleListResponse(BaseModel):
    lignes: List[TarificationGrilleFinaleRowResponse]


class CanonicalVoyageZoneItem(BaseModel):
    """Zone utilisée par la grille JSON voyage (devis automatique)."""

    code: str
    description: str


class CanonicalVoyageZonesResponse(BaseModel):
    """Référence unique pour l’alignement admin : codes zone = liaisons pays."""

    zones: List[CanonicalVoyageZoneItem]
    form_alignment_hint: str
