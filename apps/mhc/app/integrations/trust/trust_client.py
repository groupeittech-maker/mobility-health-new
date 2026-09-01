"""Client HTTP Trust (signature, horodatage, audit)."""
from __future__ import annotations

from app.integrations.base import BaseServiceClient
from app.integrations.trust.schemas import TrustSignRequest, TrustSignResponse


class TrustLiveClient(BaseServiceClient):
    service_name = "trust"

    def sign_document(self, request: TrustSignRequest) -> TrustSignResponse:
        data = self._request(
            "POST",
            "/v1/trust/sign",
            json=request.model_dump(mode="json", exclude_none=True),
        )
        return TrustSignResponse.model_validate(data)
