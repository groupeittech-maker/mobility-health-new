"""Client HTTP vers le Payment Orchestrator (contrat v1)."""
from __future__ import annotations

from app.integrations.base import BaseServiceClient
from app.integrations.payment.schemas import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentStatusResponse,
)


class PaymentLiveClient(BaseServiceClient):
    service_name = "payment"

    def create_intent(self, request: PaymentIntentRequest) -> PaymentIntentResponse:
        data = self._request(
            "POST",
            "/v1/payments/intents",
            json=request.model_dump(mode="json"),
        )
        return PaymentIntentResponse.model_validate(data)

    def get_status(self, payment_id: str) -> PaymentStatusResponse:
        data = self._request("GET", f"/v1/payments/{payment_id}")
        return PaymentStatusResponse.model_validate(data)
