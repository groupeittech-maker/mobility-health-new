"""Client HTTP vers l'orchestrateur de paiement AfriPaie.

API réelle (docs/INTEGRATION.md du projet AfriPaie) :
- POST /v1/payments            — encaissement direct (push USSD, redirect carte…)
- POST /v1/checkout-sessions   — session de paiement hébergée (page AfriPaie)
- GET  /v1/payments/{id}       — statut d'un paiement (fait avancer l'état)
- GET  /v1/checkout-sessions/{id} — session + paiement associé
- Webhooks sortants signés `Afripaie-Signature: t=<ts>,v1=<hmac>` (voir webhook.py)

Tous les montants sont des entiers en unités mineures côté AfriPaie.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.integrations.base import BaseServiceClient
from app.integrations.payment.schemas import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentStatusResponse,
    to_minor_units,
)

# Statuts AfriPaie (majuscules) → statuts du contrat MHC.
_STATUS_MAP = {
    "CREATED": "pending",
    "OPEN": "pending",
    "PROCESSING": "processing",
    "AWAITING_CUSTOMER": "processing",
    "SUCCEEDED": "success",
    "COMPLETED": "success",
    "FAILED": "failed",
    "EXPIRED": "expired",
    "CANCELLED": "expired",
    "UNKNOWN": "processing",
}


def _map_status(status: Optional[str]) -> str:
    return _STATUS_MAP.get((status or "").upper(), "pending")


class PaymentLiveClient(BaseServiceClient):
    service_name = "afripaie"

    # ------------------------------------------------------------------ #
    # Création                                                            #
    # ------------------------------------------------------------------ #

    def create_intent(self, request: PaymentIntentRequest) -> PaymentIntentResponse:
        if request.flow == "checkout":
            return self._create_checkout_session(request)
        return self._create_payment(request)

    def _create_checkout_session(
        self, request: PaymentIntentRequest
    ) -> PaymentIntentResponse:
        body: Dict[str, Any] = {
            "reference": request.reference,
            "amount": to_minor_units(request.amount, request.currency),
            "currency": request.currency,
        }
        if request.country:
            body["country"] = request.country
        if request.description:
            body["description"] = request.description
        customer = {
            k: v
            for k, v in {
                "phone": request.customer.phone,
                "email": request.customer.email,
                "name": request.customer.name,
            }.items()
            if v
        }
        if customer:
            body["customer"] = customer
        if request.success_url:
            body["success_url"] = request.success_url
        if request.cancel_url:
            body["cancel_url"] = request.cancel_url
        if request.metadata:
            body["metadata"] = {str(k): str(v) for k, v in request.metadata.items()}

        data = self._request(
            "POST",
            "/v1/checkout-sessions",
            json=body,
            extra_headers=self._idempotency_headers(request),
        )
        return PaymentIntentResponse(
            payment_id=data.get("id", ""),
            status=_map_status(data.get("status")),  # OPEN → pending
            checkout_url=data.get("url"),
            action_type="redirect" if data.get("url") else None,
            expires_at=data.get("expires_at"),
        )

    def _create_payment(self, request: PaymentIntentRequest) -> PaymentIntentResponse:
        body: Dict[str, Any] = {
            "reference": request.reference,
            "amount": to_minor_units(request.amount, request.currency),
            "currency": request.currency,
            "channel": request.method,
            "customer": {
                k: v
                for k, v in {
                    "phone": request.customer.phone,
                    "email": request.customer.email,
                    "name": request.customer.name,
                }.items()
                if v
            },
        }
        if request.country:
            body["country"] = request.country
        if request.network:
            body["network"] = request.network
        if request.description:
            body["description"] = request.description
        if request.return_url:
            body["return_url"] = request.return_url
        if request.metadata:
            body["metadata"] = {str(k): str(v) for k, v in request.metadata.items()}

        data = self._request(
            "POST",
            "/v1/payments",
            json=body,
            extra_headers=self._idempotency_headers(request),
        )
        action = data.get("action") or {}
        provider = data.get("provider") or {}
        return PaymentIntentResponse(
            payment_id=data.get("id", ""),
            status=_map_status(data.get("status")),
            provider=provider.get("id") if isinstance(provider, dict) else provider,
            checkout_url=action.get("url") if action.get("type") == "redirect" else None,
            action_type=action.get("type") or "none",
            instructions=action.get("instructions"),
            expires_at=action.get("expiresAt") or action.get("expires_at"),
        )

    # ------------------------------------------------------------------ #
    # Statut                                                              #
    # ------------------------------------------------------------------ #

    def get_status(self, payment_id: str) -> PaymentStatusResponse:
        if payment_id.startswith("cs_"):
            # Session hébergée : on lit la session puis le paiement associé.
            session = self._request("GET", f"/v1/checkout-sessions/{payment_id}")
            payment = session.get("payment") or {}
            if payment:
                return self._status_from_payment(payment)
            # Pas encore de paiement : la session est ouverte ou expirée.
            return PaymentStatusResponse(
                payment_id=session.get("id", payment_id),
                status=_map_status(session.get("status")),
                reference=session.get("reference", ""),
                amount=self._major_units(session.get("amount"), session.get("currency")),
                currency=session.get("currency", "XAF"),
                paid_at=None,
            )
        data = self._request("GET", f"/v1/payments/{payment_id}")
        return self._status_from_payment(data)

    def _status_from_payment(self, data: Dict[str, Any]) -> PaymentStatusResponse:
        provider = data.get("provider")
        failure = data.get("failure") or {}
        return PaymentStatusResponse(
            payment_id=data.get("id", ""),
            status=_map_status(data.get("status")),  # type: ignore[arg-type]
            reference=data.get("reference", ""),
            amount=self._major_units(data.get("amount"), data.get("currency")),
            currency=data.get("currency", "XAF"),
            provider=provider.get("id") if isinstance(provider, dict) else provider,
            failure_code=failure.get("code"),
            failure_message=failure.get("message"),
            paid_at=data.get("succeeded_at") or data.get("paid_at"),
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _idempotency_headers(request: PaymentIntentRequest) -> Dict[str, str]:
        key = request.idempotency_key or request.reference
        return {"Idempotency-Key": key} if key else {}

    @staticmethod
    def _major_units(amount: Any, currency: Optional[str]) -> "Any":
        """Reconvertit un montant en unités mineures vers l'unité principale."""
        from decimal import Decimal

        from app.integrations.payment.schemas import CURRENCY_EXPONENTS

        if amount is None:
            return Decimal("0")
        exponent = CURRENCY_EXPONENTS.get((currency or "XAF").upper(), 0)
        return Decimal(str(amount)) / Decimal(10**exponent)
