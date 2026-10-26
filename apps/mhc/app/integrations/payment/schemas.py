"""Schémas d'intégration paiement — alignés sur l'API AfriPaie (orchestrateur)."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Canaux acceptés par AfriPaie (POST /v1/payments).
PaymentChannel = Literal["mobile_money", "card", "bank_transfer"]

# Exposants des devises : nombre de décimales en unités mineures.
# AfriPaie exige des montants entiers (jamais de décimales).
CURRENCY_EXPONENTS = {
    "XAF": 0, "XOF": 0, "CFA": 0,
    "NGN": 2, "KES": 2, "GHS": 2, "USD": 2, "EUR": 2,
    "TND": 3, "LYD": 3,
}


def to_minor_units(amount: Decimal, currency: str) -> int:
    """Convertit un montant décimal en unités mineures entières pour AfriPaie."""
    exponent = CURRENCY_EXPONENTS.get((currency or "XAF").upper(), 0)
    minor = int(round(amount * (10 ** exponent)))
    if minor <= 0:
        raise ValueError(f"Montant invalide pour le paiement : {amount} {currency}")
    return minor


class PaymentCustomer(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


class PaymentIntentRequest(BaseModel):
    amount: Decimal
    currency: str = "XAF"
    country: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="Code ISO-2 ; facultatif — AfriPaie déduit le pays de l'indicatif téléphonique",
    )
    reference: str = Field(..., description="Référence métier MHC (ex. numéro souscription)")
    method: PaymentChannel = "mobile_money"
    network: Optional[str] = Field(
        default=None, description="Réseau mobile money explicite (ex. MTN_CG)"
    )
    customer: PaymentCustomer
    description: Optional[str] = None
    # Parcours : "direct" = push USSD/OTP sur le téléphone du client,
    # "checkout" = session hébergée AfriPaie (page de paiement).
    flow: Literal["direct", "checkout"] = "direct"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    return_url: Optional[str] = None
    callback_url: Optional[str] = None
    metadata: Optional[dict] = None
    idempotency_key: Optional[str] = None


class PaymentIntentResponse(BaseModel):
    payment_id: str
    status: Literal["pending", "processing", "success", "failed", "expired"] = "pending"
    provider: Optional[str] = None
    checkout_url: Optional[str] = None
    action_type: Optional[Literal["ussd_push", "otp_required", "redirect", "none"]] = None
    instructions: Optional[str] = None
    expires_at: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    payment_id: str
    status: Literal["pending", "processing", "success", "failed", "expired", "refunded"]
    reference: str
    amount: Decimal
    currency: str
    provider: Optional[str] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    paid_at: Optional[str] = None
