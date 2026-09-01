"""Schémas alignés sur contracts/trust-api.v1.md."""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class IdentityVerifyRequest(BaseModel):
    reference: str = Field(..., description="Référence métier MHC (user_id, souscription…)")
    document_type: str = "passeport"
    document_file_url: Optional[str] = None
    selfie_file_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IdentityVerifyResponse(BaseModel):
    session_id: str
    status: Literal["pending", "verified", "rejected"] = "pending"
    confidence: float = 0.0
    details: Optional[Dict[str, Any]] = None


class TrustSignRequest(BaseModel):
    reference: str
    document_hash: str
    document_type: str = "attestation"
    metadata: Optional[Dict[str, Any]] = None


class TrustSignResponse(BaseModel):
    proof_id: str
    document_hash: str
    signature: Optional[str] = None
    timestamp: Optional[str] = None
    audit_chain_hash: Optional[str] = None
