"""Stub Payment — comportement local quand l'orchestrateur n'est pas branché."""
from __future__ import annotations

import uuid

from app.integrations.payment.schemas import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentStatusResponse,
)


class PaymentStubClient:
    """Simule l'orchestrateur AfriPaie en mode développement/test."""

    def create_intent(self, request: PaymentIntentRequest) -> PaymentIntentResponse:
        payment_id = f"stub_{uuid.uuid4().hex[:12]}"
        if request.flow == "checkout":
            return PaymentIntentResponse(
                payment_id=payment_id,
                status="pending",
                provider="stub",
                checkout_url=(
                    f"https://checkout.stub.mobility-health.africa/pay/{payment_id}"
                    f"?ref={request.reference}"
                ),
                action_type="redirect",
            )
        return PaymentIntentResponse(
            payment_id=payment_id,
            status="processing",
            provider="stub",
            action_type="ussd_push",
            instructions=(
                "Une demande de paiement a été envoyée sur le téléphone du client (stub)."
            ),
        )

    def get_status(self, payment_id: str) -> PaymentStatusResponse:
        return PaymentStatusResponse(
            payment_id=payment_id,
            status="pending",
            reference="stub",
            amount=0,
            currency="XAF",
            provider="stub",
            paid_at=None,
        )
