"""Schémas alignés sur contracts/ekyc-api.v1.md (IT-TECH eKYC)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class EkycIdentity(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    issuing_country: Optional[str] = None
    expiry_date: Optional[str] = None
    sex: Optional[str] = None


class EkycSessionRequest(BaseModel):
    customer_reference: str = Field(
        ..., description="Référence métier MHC (ex. user_id, souscription_id)"
    )
    flow: Literal["TRAVEL_INSURANCE", "BANK_ACCOUNT", "CITIZEN"] = "TRAVEL_INSURANCE"
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Données opaques renvoyées telles quelles"
    )


class EkycSessionResponse(BaseModel):
    session_id: str
    status: Literal["CREATED", "IN_PROGRESS", "PROCESSING", "VERIFIED", "REJECTED", "REVIEW", "EXPIRED"]
    flow: str
    verification_url: str
    expires_at: Optional[str] = None


class EkycResultResponse(BaseModel):
    session_id: str
    customer_reference: Optional[str] = None
    flow: str
    status: Literal["CREATED", "IN_PROGRESS", "PROCESSING", "VERIFIED", "REJECTED", "REVIEW", "EXPIRED"]
    checks: Dict[str, Any] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    identity: Optional[EkycIdentity] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

    @property
    def is_terminal(self) -> bool:
        return self.status in {"VERIFIED", "REJECTED", "REVIEW", "EXPIRED"}

    @property
    def is_verified(self) -> bool:
        return self.status == "VERIFIED"


class EkycSealRequest(BaseModel):
    document_reference: str = Field(..., description="Référence du document métier MHC")
    title: Optional[str] = None
    fields: Optional[Dict[str, Any]] = Field(
        default=None, description="Couples clé/valeur à imprimer dans le contrat généré"
    )
    pdf_base64: Optional[str] = Field(
        default=None,
        description="PDF déjà généré (base64). Si absent, un PDF est généré à partir des champs",
    )


class EkycSealResponse(BaseModel):
    signed_document_id: str
    session_id: str
    document_reference: str
    sha256: str
    signature_algorithm: Optional[str] = None
    certificate_fingerprint: Optional[str] = None
    timestamp_authority: Optional[str] = None
    timestamp_qualified: bool = False
    timestamped_at: Optional[str] = None
    download_url: Optional[str] = None


class EkycWebhookPayload(BaseModel):
    event: Literal["KYC_VERIFIED", "KYC_REJECTED", "KYC_REVIEW_REQUIRED", "KYC_EXPIRED"]
    session_id: str
    customer_reference: Optional[str] = None
    flow: Optional[str] = None
    status: Optional[str] = None
    occurred_at: Optional[str] = None
