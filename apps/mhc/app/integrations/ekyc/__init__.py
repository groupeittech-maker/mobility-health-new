"""Intégration IT-TECH eKYC — session, résultat, scellement, webhooks."""
from __future__ import annotations

from typing import Any, Literal, Protocol

from app.core.config import settings
from app.integrations.ekyc.client import (
    EkycLiveClient,
    extract_ekyc_webhook_headers,
    verify_ekyc_webhook,
)
from app.integrations.ekyc.schemas import (
    EkycResultResponse,
    EkycSealResponse,
    EkycSessionResponse,
    EkycWebhookPayload,
)
from app.integrations.ekyc.stub import EkycStubClient


class EkycClient(Protocol):
    """Contrat consommé par MHC."""

    def create_session(
        self,
        customer_reference: str,
        flow: str,
        metadata: dict[str, Any] | None = None,
    ) -> EkycSessionResponse: ...

    def get_result(self, session_id: str) -> EkycResultResponse: ...

    def seal_document(
        self,
        session_id: str,
        document_reference: str,
        title: str | None = None,
        fields: dict[str, Any] | None = None,
        pdf_base64: str | None = None,
    ) -> EkycSealResponse: ...


def get_ekyc_client() -> EkycClient:
    """Factory : retourne le client ``live`` ou ``stub`` selon la configuration."""
    mode: Literal["stub", "live"] = settings.EKYC_SERVICE_MODE  # type: ignore[assignment]
    if mode == "live":
        return EkycLiveClient(
            base_url=settings.EKYC_SERVICE_URL,
            api_key=settings.EKYC_SERVICE_CLIENT_ID,
            api_secret=settings.EKYC_SERVICE_CLIENT_SECRET,
        )
    return EkycStubClient()

__all__ = [
    "EkycClient",
    "EkycLiveClient",
    "EkycStubClient",
    "EkycResultResponse",
    "EkycSealResponse",
    "EkycSessionResponse",
    "EkycWebhookPayload",
    "get_ekyc_client",
    "verify_ekyc_webhook",
    "extract_ekyc_webhook_headers",
]
