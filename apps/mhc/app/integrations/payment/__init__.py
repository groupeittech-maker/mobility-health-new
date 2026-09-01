"""Intégration Payment Orchestrator (phase 4 — stub jusqu'au branchement live)."""
from __future__ import annotations

from typing import Literal, Protocol

from app.core.config import settings
from app.integrations.payment.schemas import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentStatusResponse,
)
from app.integrations.payment.stub import PaymentStubClient


class PaymentClient(Protocol):
    def create_intent(self, request: PaymentIntentRequest) -> PaymentIntentResponse: ...
    def get_status(self, payment_id: str) -> PaymentStatusResponse: ...


def get_payment_client() -> PaymentClient:
    mode: Literal["stub", "live"] = settings.PAYMENT_SERVICE_MODE  # type: ignore[assignment]
    if mode == "live":
        from app.integrations.payment.client import PaymentLiveClient

        return PaymentLiveClient(
            base_url=settings.PAYMENT_SERVICE_URL,
            api_key=settings.PAYMENT_SERVICE_API_KEY,
        )
    return PaymentStubClient()
