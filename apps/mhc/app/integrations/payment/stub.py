"""Stub Payment — comportement local actuel jusqu'à phase 4 (orchestrateur branché)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.integrations.payment.schemas import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentStatusResponse,
)


class PaymentStubClient:
    """Simule l'orchestrateur ; les appels réels restent dans payments.py pour l'instant."""

    def create_intent(self, request: PaymentIntentRequest) -> PaymentIntentResponse:
        return PaymentIntentResponse(
            payment_id=f"stub_{uuid.uuid4().hex[:12]}",
            status="pending",
            provider="stub",
            checkout_url=None,
        )

    def get_status(self, payment_id: str) -> PaymentStatusResponse:
        return PaymentStatusResponse(
            payment_id=payment_id,
            status="pending",
            reference="stub",
            amount=0,
            currency="XAF",
            paid_at=None,
        )
