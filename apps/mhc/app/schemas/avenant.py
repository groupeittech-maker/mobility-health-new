from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AnnulationRequest(BaseModel):
    """`confirmer=false` : simulation (montant remboursable) sans rien modifier."""

    confirmer: bool = False
    motif: Optional[str] = None


class ModificationRequest(BaseModel):
    """Nouvelle destination dans la même zone tarifaire ; dates inchangées."""

    destination_country_id: int
    destination_ville: Optional[str] = None
    confirmer: bool = False
    motif: Optional[str] = None


class ProrogationRequest(BaseModel):
    nouvelle_date_fin: date
    confirmer: bool = False
    motif: Optional[str] = None


class AvenantPaymentRequest(BaseModel):
    payment_type: str = "mobile_money_mtn"
    flow: str = Field(default="checkout", pattern="^(checkout|direct)$")


class RistourneConfirmRequest(BaseModel):
    moyen_remboursement: str
    reference: Optional[str] = None


class AvenantResponse(BaseModel):
    id: int
    souscription_id: int
    type_avenant: str
    numero: str
    statut: str
    motif_autre: Optional[str] = None
    date_effet: Optional[datetime] = None
    date_echeance: Optional[datetime] = None
    date_debut_initiale: Optional[datetime] = None
    date_fin_initiale: Optional[datetime] = None
    nouvelle_date_debut: Optional[datetime] = None
    nouvelle_date_fin: Optional[datetime] = None
    montant_ajustement: Optional[Decimal] = None
    nature_ajustement: Optional[str] = None
    paiement_id: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RistourneResponse(BaseModel):
    id: int
    souscription_id: int
    avenant_id: Optional[int] = None
    paiement_id: Optional[int] = None
    numero: Optional[str] = None
    statut: str
    motif: Optional[str] = None
    montant_prime: Decimal
    montant_frais_police: Decimal
    montant_taxes: Decimal
    montant_total: Decimal
    devise: str
    moyen_remboursement: Optional[str] = None
    reference_remboursement: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ActionAvailability(BaseModel):
    disponible: bool
    motif: Optional[str] = None


class PolicyActionsResponse(BaseModel):
    souscription_id: int
    statut_souscription: str
    actions: Dict[str, ActionAvailability]
    action_en_cours: Optional[AvenantResponse] = None
    duree_max_jours: int
    avenants: List[AvenantResponse] = []
    ristournes: List[RistourneResponse] = []


class MontantsResponse(BaseModel):
    prime: Decimal
    frais_police: Decimal
    frais_services: Decimal
    taxes: Decimal
    total: Decimal


class PolicyActionResult(BaseModel):
    souscription_id: int
    statut_souscription: str
    simulation: bool
    nature_ajustement: Optional[str] = None
    montants: Optional[MontantsResponse] = None
    avenant: Optional[AvenantResponse] = None
    ristourne: Optional[RistourneResponse] = None
    paiement_id: Optional[int] = None
    payment_status: Optional[str] = None
    payment_url: Optional[str] = None
    payment_instructions: Optional[Any] = None
    ancienne_destination: Optional[str] = None
    nouvelle_destination: Optional[str] = None
    zone_tarifaire: Optional[str] = None
