"""Intégration IT-TECH eKYC — session, résultat, scellement, webhooks."""
from __future__ import annotations

import threading
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


# Le client live est un singleton : son cache de token OAuth (expires_in)
# doit survivre entre les appels. Sans singleton, chaque opération
# (création de session, polling, evidence…) demandait un nouveau token
# et épuisait la limite eKYC (10 émissions / 10 min / client_id → 429).
# Clé = configuration : un changement de base_url/credentials (tests,
# reload) produit une nouvelle instance au lieu d'un client périmé.
_live_client: EkycLiveClient | None = None
_live_client_key: tuple[str, str] | None = None
_live_client_lock = threading.Lock()


def get_ekyc_client() -> EkycClient:
    """Factory : retourne le client ``live`` ou ``stub`` selon la configuration."""
    global _live_client, _live_client_key
    mode: Literal["stub", "live"] = settings.EKYC_SERVICE_MODE  # type: ignore[assignment]
    if mode == "live":
        key = (settings.EKYC_SERVICE_URL, settings.EKYC_SERVICE_CLIENT_ID)
        if _live_client is None or _live_client_key != key:
            with _live_client_lock:
                if _live_client is None or _live_client_key != key:
                    _live_client = EkycLiveClient(
                        base_url=settings.EKYC_SERVICE_URL,
                        api_key=settings.EKYC_SERVICE_CLIENT_ID,
                        api_secret=settings.EKYC_SERVICE_CLIENT_SECRET,
                    )
                    _live_client_key = key
        return _live_client
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
