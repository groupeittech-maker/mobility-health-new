"""Stub Identity / Trust — no-op jusqu'à branchement Digital Trust (phase 3)."""
from __future__ import annotations

import uuid

from app.integrations.trust.schemas import (
    IdentityVerifyRequest,
    IdentityVerifyResponse,
    TrustSignRequest,
    TrustSignResponse,
)


class IdentityStubClient:
    def verify(self, request: IdentityVerifyRequest) -> IdentityVerifyResponse:
        return IdentityVerifyResponse(
            session_id=f"stub_id_{uuid.uuid4().hex[:12]}",
            status="pending",
            confidence=0.0,
            details={"message": "Digital Trust non branché — stub actif"},
        )


class TrustStubClient:
    def sign_document(self, request: TrustSignRequest) -> TrustSignResponse:
        return TrustSignResponse(
            proof_id=f"stub_proof_{uuid.uuid4().hex[:12]}",
            document_hash=request.document_hash,
            signature=None,
            timestamp=None,
            audit_chain_hash=None,
        )
