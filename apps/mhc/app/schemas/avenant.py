from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AvenantSuspensionRequest(BaseModel):
    """Demande de suspension : motifs cochés + précision + pièces (optionnel)."""

    motifs: List[str] = []
    motif_autre: Optional[str] = None
    pieces: List[str] = []


class AvenantSuspensionDecision(BaseModel):
    """Décision de l'Assureur sur une demande de suspension."""

    approve: bool
    date_effet: Optional[datetime] = None
    notes: Optional[str] = None


class AvenantReemissionRequest(BaseModel):
    date_effet: Optional[datetime] = None


class AvenantResponse(BaseModel):
    id: int
    souscription_id: int
    type_avenant: str
    numero: str
    statut: str
    motifs: Optional[List[str]] = None
    motif_autre: Optional[str] = None
    pieces_jointes: Optional[List[str]] = None
    decision_assureur: Optional[str] = None
    date_effet: Optional[datetime] = None
    date_echeance: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AvenantCatalogResponse(BaseModel):
    """Catalogue des motifs et pièces (clé → libellé) pour l'UI de suspension."""

    motifs: dict
    pieces: dict
