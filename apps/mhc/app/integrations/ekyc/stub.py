"""Stub eKYC — retourne des sessions déterministes sans appeler de service externe.

Le mode ``stub`` permet à MHC de fonctionner hors-ligne en attendant le
branchement de l'eKYC IT-TECH, et de valider le parcours en tests.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from app.integrations.ekyc.schemas import (
    EkycIdentity,
    EkycResultResponse,
    EkycSealResponse,
    EkycSessionResponse,
)


class EkycStubClient:
    """Implémentation stub de l'interface eKYC.

    - ``create_session`` génère une session immédiatement ``CREATED``.
    - ``get_result`` retourne ``VERIFIED`` avec une identité fictive
      (sauf si ``metadata._force_status`` est fourni pour les tests).
    - ``seal_document`` retourne un document scellé fictif.
    """

    _sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(
        self,
        customer_reference: str,
        flow: str,
        metadata: Dict[str, Any] | None = None,
    ) -> EkycSessionResponse:
        session_id = f"KYC-STUB-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(minutes=15)).isoformat()
        self._sessions[session_id] = {
            "customer_reference": customer_reference,
            "flow": flow,
            "metadata": metadata or {},
            "created_at": now.isoformat(),
            "status": "CREATED",
        }
        return EkycSessionResponse(
            session_id=session_id,
            status="CREATED",
            flow=flow,
            verification_url=f"http://localhost:8000/verify/{session_id}?token=stub-token",
            expires_at=expires,
        )

    def get_result(self, session_id: str) -> EkycResultResponse:
        session = self._sessions.get(session_id)
        if session is None:
            # Fallback : si l'appelant demande une inconnue, on simule un rejet clair.
            return EkycResultResponse(
                session_id=session_id,
                flow="TRAVEL_INSURANCE",
                status="REJECTED",
                reasons=["SESSION_NOT_FOUND_STUB"],
            )

        forced = (session.get("metadata") or {}).get("_force_status")
        status = forced if forced in {"VERIFIED", "REJECTED", "REVIEW", "EXPIRED"} else "VERIFIED"

        identity = None
        if status in {"VERIFIED", "REVIEW"}:
            identity = EkycIdentity(
                first_name="John",
                last_name="DOE",
                date_of_birth="1990-05-15",
                nationality="CIV",
                document_type="PASSPORT",
                document_number="AB123456",
                issuing_country="CIV",
                expiry_date="2030-12-31",
                sex="M",
            )

        return EkycResultResponse(
            session_id=session_id,
            customer_reference=session.get("customer_reference"),
            flow=session.get("flow", "TRAVEL_INSURANCE"),
            status=status,
            checks={
                "DOCUMENT_VERIFICATION": "PASSED",
                "LIVENESS": "PASSED",
                "FACE_MATCH": "PASSED",
                "OTP": "PASSED",
            },
            reasons=[],
            identity=identity,
            created_at=session.get("created_at"),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    def seal_document(
        self,
        session_id: str,
        document_reference: str,
        title: str | None = None,
        fields: Dict[str, Any] | None = None,
        pdf_base64: str | None = None,
    ) -> EkycSealResponse:
        return EkycSealResponse(
            signed_document_id=f"signed-{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            document_reference=document_reference,
            sha256=f"sha256-{uuid.uuid4().hex}",
            signature_algorithm="RSASSA-PKCS1-v1_5-SHA256",
            certificate_fingerprint="stub-fingerprint",
            timestamp_authority="local",
            timestamp_qualified=False,
            timestamped_at=datetime.now(timezone.utc).isoformat(),
            download_url=f"/v1/kyc/sessions/{session_id}/documents/signed-stub",
        )
