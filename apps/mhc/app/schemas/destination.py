from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class MedecinConseilContact(BaseModel):
    id: int
    nom: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None


class DestinationCityBase(BaseModel):
    nom: str
    est_actif: bool = True
    ordre_affichage: int = 0
    notes: Optional[str] = None


class DestinationCityCreate(DestinationCityBase):
    pays_id: int


class DestinationCityUpdate(BaseModel):
    nom: Optional[str] = None
    est_actif: Optional[bool] = None
    ordre_affichage: Optional[int] = None
    notes: Optional[str] = None


class DestinationCityResponse(DestinationCityBase):
    id: int
    pays_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DestinationCountryBase(BaseModel):
    code: str
    nom: str
    est_actif: bool = True
    ordre_affichage: int = 0
    notes: Optional[str] = None
    medecin_conseil_id: Optional[int] = None


class DestinationCountryCreate(DestinationCountryBase):
    pass


class DestinationCountryUpdate(BaseModel):
    code: Optional[str] = None
    nom: Optional[str] = None
    est_actif: Optional[bool] = None
    ordre_affichage: Optional[int] = None
    notes: Optional[str] = None
    medecin_conseil_id: Optional[int] = None


class DestinationCountryResponse(DestinationCountryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    villes: List[DestinationCityResponse] = []
    medecin_conseil: Optional[MedecinConseilContact] = None
    
    model_config = ConfigDict(from_attributes=True)


class DestinationCountryWithCitiesResponse(DestinationCountryResponse):
    """Réponse avec les villes incluses"""
    villes: List[DestinationCityResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

