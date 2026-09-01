from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.core.enums import StatutPaiement, TypePaiement


class PaiementBase(BaseModel):
    montant: Decimal
    type_paiement: TypePaiement
    statut: StatutPaiement = StatutPaiement.EN_ATTENTE
    date_paiement: Optional[datetime] = None
    reference_transaction: Optional[str] = None
    reference_externe: Optional[str] = None
    notes: Optional[str] = None
    montant_rembourse: Optional[Decimal] = None


class PaiementCreate(PaiementBase):
    souscription_id: int
    user_id: int


class PaiementUpdate(BaseModel):
    montant: Optional[Decimal] = None
    type_paiement: Optional[TypePaiement] = None
    statut: Optional[StatutPaiement] = None
    date_paiement: Optional[datetime] = None
    reference_transaction: Optional[str] = None
    reference_externe: Optional[str] = None
    notes: Optional[str] = None
    montant_rembourse: Optional[Decimal] = None


class PaiementResponse(PaiementBase):
    id: int
    souscription_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AccountingTransaction(BaseModel):
    payment_id: int
    subscription_id: int
    numero_souscription: str
    assure: str
    montant_total: Decimal
    montant_assureur: Decimal
    montant_courtier: Optional[Decimal] = None
    montant_mh: Decimal
    montant_assure: Optional[Decimal] = None
    statut_transaction: str
    status_code: str
    action: Optional[str] = None
    reference_transaction: Optional[str] = None
    date_paiement: Optional[datetime] = None
    produit_id: Optional[int] = None
    produit_nom: Optional[str] = None
    assureur_id: Optional[int] = None
    assureur_nom: Optional[str] = None
    courtier_id: Optional[int] = None
    courtier_nom: Optional[str] = None
    commission_courtier_pct: Optional[Decimal] = None
    # Déprécié pour les encaissements souscription : la répartition utilise prime_assurance / frais_services (plus de % sur le total).
    commission_assureur_pct: Optional[Decimal] = None