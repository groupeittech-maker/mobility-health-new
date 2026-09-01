"""Schémas alignés sur contracts/payment-api.v1.md (contrat public IT-Tech)."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PaymentCustomer(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


class PaymentIntentRequest(BaseModel):
    amount: Decimal
    currency: str = "XAF"
    country: str = Field(..., min_length=2, max_length=2)
    reference: str = Field(..., description="Référence métier MHC (ex. numéro souscription)")
    method: Literal[
        "mobile_money",
        "card",
        "bank_transfer",
    ] = "mobile_money"
    customer: PaymentCustomer
    callback_url: Optional[str] = None
    metadata: Optional[dict] = None


class PaymentIntentResponse(BaseModel):
    payment_id: str
    status: Literal["pending", "processing", "success", "failed", "expired"] = "pending"
    provider: Optional[str] = None
    checkout_url: Optional[str] = None
    expires_at: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    payment_id: str
    status: Literal["pending", "processing", "success", "failed", "expired", "refunded"]
    reference: str
    amount: Decimal
    currency: str
    paid_at: Optional[str] = None
