"""Workflow MyMHC V3 : purge des brouillons / approuvés non payés, rappels J-2 et
veille, refus eKYC et limite de 92 jours à la création du voyage."""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.enums import StatutSouscription
from app.models.ekyc_session import EkycSession
from app.models.souscription import Souscription
from app.services import subscription_cleanup
from app.services.subscription_decision_service import SubscriptionDecisionEngine

NOW = datetime(2026, 10, 26, 10, 0)
_SEQ = {"n": 0}


@pytest.fixture
def notifications(monkeypatch):
    from app.services.notification_service import NotificationService

    sent = []
    monkeypatch.setattr(NotificationService, "create_notification", staticmethod(lambda **kw: sent.append(kw)))
    return sent


def _sous(db, user, test_product, *, start_offset_days, statut=StatutSouscription.EN_ATTENTE_PAIEMENT):
    _SEQ["n"] += 1
    product = test_product(db, code=f"CLN-{_SEQ['n']}")
    sous = Souscription(
        user_id=user.id,
        produit_assurance_id=product.id,
        numero_souscription=f"CLN-{_SEQ['n']}",
        prix_applique=Decimal("100"),
        date_debut=NOW + timedelta(days=start_offset_days),
        date_fin=NOW + timedelta(days=start_offset_days + 10),
        statut=statut,
    )
    db.add(sous)
    db.commit()
    return sous


class TestPurge:
    def test_deleted_only_after_end_of_start_day(self, db, test_user, test_product):
        today = _sous(db, test_user, test_product, start_offset_days=0)
        yesterday = _sous(db, test_user, test_product, start_offset_days=-1, statut=StatutSouscription.EN_ATTENTE)
        active = _sous(db, test_user, test_product, start_offset_days=-1, statut=StatutSouscription.ACTIVE)
        in_review = _sous(db, test_user, test_product, start_offset_days=-1, statut=StatutSouscription.EN_ATTENTE_VALIDATION)
        ids = {s.id for s in (today, yesterday, active, in_review)}

        assert subscription_cleanup.purge_stale_subscriptions(db, now=NOW) == 1
        remaining = {s.id for s in db.query(Souscription).filter(Souscription.id.in_(ids))}
        assert yesterday.id not in remaining
        assert {today.id, active.id, in_review.id} <= remaining


class TestReminders:
    def test_reminders_two_days_before_and_eve(self, db, test_user, test_product, notifications):
        j2 = _sous(db, test_user, test_product, start_offset_days=2)
        eve = _sous(db, test_user, test_product, start_offset_days=1, statut=StatutSouscription.EN_ATTENTE)
        _sous(db, test_user, test_product, start_offset_days=5)
        _sous(db, test_user, test_product, start_offset_days=1, statut=StatutSouscription.ACTIVE)

        assert subscription_cleanup.send_deletion_reminders(db, now=NOW) == 2
        by_id = {n["lien_relation_id"]: n["message"] for n in notifications}
        assert set(by_id) == {j2.id, eve.id}
        assert "dans 2 jours" in by_id[j2.id]
        assert "demain" in by_id[eve.id] and "brouillon" in by_id[eve.id]


class TestEkycRefusal:
    def test_rejected_ekyc_goes_to_production_review_not_auto_reject(
        self, db, test_user, test_product, monkeypatch
    ):
        """Politique produit : échec eKYC → REVIEW manuelle, jamais refus auto."""
        monkeypatch.setattr(SubscriptionDecisionEngine, "_notify_client_outcome", staticmethod(lambda *a, **k: None))
        sous = _sous(db, test_user, test_product, start_offset_days=10, statut=StatutSouscription.EN_ATTENTE)
        db.add(EkycSession(
            session_id="KYC-1", customer_reference="C-1", user_id=test_user.id,
            souscription_id=sous.id, status="REJECTED",
        ))
        db.commit()
        result = SubscriptionDecisionEngine.evaluate(db, sous)
        assert result.decision == "review"
        assert sous.statut == StatutSouscription.EN_ATTENTE_VALIDATION
        assert "production" in result.review_steps


class TestTripWindow:
    def test_project_longer_than_92_days_rejected(self, client, auth_headers):
        start = datetime.utcnow() + timedelta(days=3)
        payload = {
            "titre": "Long séjour",
            "destination": "France",
            "date_depart": start.isoformat(),
            "date_retour": (start + timedelta(days=93)).isoformat(),
        }
        r = client.post("/api/v1/voyages/", json=payload, headers=auth_headers)
        assert r.status_code == 400
        assert "92" in r.json()["detail"]

    def test_project_in_the_past_rejected(self, client, auth_headers):
        start = datetime.utcnow() - timedelta(days=2)
        payload = {
            "titre": "Passé",
            "destination": "France",
            "date_depart": start.isoformat(),
            "date_retour": (start + timedelta(days=5)).isoformat(),
        }
        r = client.post("/api/v1/voyages/", json=payload, headers=auth_headers)
        assert r.status_code == 400
