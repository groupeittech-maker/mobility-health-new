"""Intégration Digital Trust — Identity + Trust (phase 3)."""
from __future__ import annotations

from typing import Literal, Protocol

from app.core.config import settings
from app.integrations.trust.schemas import (
    IdentityVerifyRequest,
    IdentityVerifyResponse,
    TrustSignRequest,
    TrustSignResponse,
)
from app.integrations.trust.stub import IdentityStubClient, TrustStubClient


class IdentityClient(Protocol):
    def verify(self, request: IdentityVerifyRequest) -> IdentityVerifyResponse: ...


class TrustClient(Protocol):
    def sign_document(self, request: TrustSignRequest) -> TrustSignResponse: ...


def get_identity_client() -> IdentityClient:
    mode: Literal["stub", "live"] = settings.TRUST_SERVICE_MODE  # type: ignore[assignment]
    if mode == "live":
        from app.integrations.trust.identity_client import IdentityLiveClient

        return IdentityLiveClient(
            base_url=settings.TRUST_SERVICE_URL,
            api_key=settings.TRUST_SERVICE_API_KEY,
        )
    return IdentityStubClient()


def get_trust_client() -> TrustClient:
    mode: Literal["stub", "live"] = settings.TRUST_SERVICE_MODE  # type: ignore[assignment]
    if mode == "live":
        from app.integrations.trust.trust_client import TrustLiveClient

        return TrustLiveClient(
            base_url=settings.TRUST_SERVICE_URL,
            api_key=settings.TRUST_SERVICE_API_KEY,
        )
    return TrustStubClient()
