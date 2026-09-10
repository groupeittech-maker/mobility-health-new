"""Tests unitaires du service quittance et de la logique de séparation paiement/finance."""
from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.finance_service import FinanceService
from app.services.payment_service import PaymentService


class TestFinanceServiceLedger:
    def test_prime_and_frais_split_explicit(self):
        sub = SimpleNamespace(prime_assurance=Decimal("50000"), frais_services=Decimal("15000"))
        part_ass, part_mh = FinanceService.ledger_prime_and_frais_split(sub, Decimal("65000"))
        assert part_ass == Decimal("50000.00")
        assert part_mh == Decimal("15000.00")

    def test_refund_policy_resiliation_retention(self):
        sub = SimpleNamespace(prime_assurance=Decimal("50000"), frais_services=Decimal("15000"))
        insured, mh = FinanceService.refund_policy_breakdown(sub, Decimal("65000"), "resiliation")
        assert mh == (Decimal("50000") * Decimal("0.30")).quantize(Decimal("0.01"))
        assert insured + mh == Decimal("65000.00")


class TestPaymentServiceGetQuittance:
    def test_get_quittance_from_notes(self):
        fake_db = object()
        payment = SimpleNamespace(user_id=1, notes=json.dumps({"quittance": {"numero": "000252-119"}}))
        user = SimpleNamespace(id=1, is_superuser=False)
        result = PaymentService.get_quittance(fake_db, payment, user)
        assert result["numero"] == "000252-119"

    def test_get_quittance_forbidden(self):
        fake_db = object()
        payment = SimpleNamespace(user_id=2, notes=json.dumps({"quittance": {}}))
        user = SimpleNamespace(id=1, is_superuser=False)
        with pytest.raises(Exception):  # HTTPException
            PaymentService.get_quittance(fake_db, payment, user)

    def test_get_quittance_not_found(self):
        fake_db = object()
        payment = SimpleNamespace(user_id=1, notes=None)
        user = SimpleNamespace(id=1, is_superuser=False)
        assert PaymentService.get_quittance(fake_db, payment, user) is None
