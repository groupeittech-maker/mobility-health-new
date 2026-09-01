"""Client HTTP Identity (eKYC) — Digital Trust platform."""
from __future__ import annotations

from app.integrations.base import BaseServiceClient
from app.integrations.trust.schemas import IdentityVerifyRequest, IdentityVerifyResponse


class IdentityLiveClient(BaseServiceClient):
    service_name = "trust-identity"

    def verify(self, request: IdentityVerifyRequest) -> IdentityVerifyResponse:
        data = self._request(
            "POST",
            "/v1/identity/verify",
            json=request.model_dump(mode="json", exclude_none=True),
        )
        return IdentityVerifyResponse.model_validate(data)
