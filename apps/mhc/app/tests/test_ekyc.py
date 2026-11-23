"""Tests de l'intégration eKYC côté MHC (stub + webhook)."""
from __future__ import annotations

import hmac
import hashlib
import json
import time

import pytest

from app.integrations.base import ExternalServiceError
from app.integrations.ekyc import EkycStubClient, get_ekyc_client, verify_ekyc_webhook
from app.integrations.ekyc.client import EkycLiveClient


class TestEkycStubClient:
    def test_create_session_returns_created(self):
        client = EkycStubClient()
        resp = client.create_session("ref-1", "TRAVEL_INSURANCE")
        assert resp.status == "CREATED"
        assert resp.flow == "TRAVEL_INSURANCE"
        assert resp.verification_url.startswith("http")

    def test_get_result_returns_verified_with_identity(self):
        client = EkycStubClient()
        session = client.create_session("ref-1", "TRAVEL_INSURANCE")
        result = client.get_result(session.session_id)
        assert result.status == "VERIFIED"
        assert result.is_verified is True
        assert result.identity is not None
        assert result.identity.document_type == "PASSPORT"

    def test_get_result_for_unknown_session_returns_rejected(self):
        client = EkycStubClient()
        result = client.get_result("KYC-UNKNOWN")
        assert result.status == "REJECTED"

    def test_seal_document_returns_signed_id(self):
        client = EkycStubClient()
        session = client.create_session("ref-1", "TRAVEL_INSURANCE")
        sealed = client.seal_document(session.session_id, document_reference="ATT-001")
        assert sealed.signed_document_id.startswith("signed-")
        assert sealed.sha256.startswith("sha256-")


class TestVerifyEkycWebhook:
    def _sign(self, secret, body, ts):
        return "sha256=" + hmac.new(
            secret.encode(), ts.encode() + b"." + body, hashlib.sha256
        ).hexdigest()

    def test_valid_webhook_is_accepted(self):
        secret = "shh"
        payload = {"event": "KYC_VERIFIED", "session_id": "s1"}
        body = json.dumps(payload).encode()
        ts = str(int(time.time()))
        sig = self._sign(secret, body, ts)
        result = verify_ekyc_webhook(secret, body, sig, ts)
        assert result.event == "KYC_VERIFIED"

    def test_tampered_signature_is_rejected(self):
        secret = "shh"
        payload = {"event": "KYC_VERIFIED", "session_id": "s1"}
        body = json.dumps(payload).encode()
        ts = str(int(time.time()))
        with pytest.raises(ExternalServiceError):
            verify_ekyc_webhook(secret, body, "sha256=bad", ts)

    def test_replayed_timestamp_is_rejected(self):
        secret = "shh"
        payload = {"event": "KYC_VERIFIED", "session_id": "s1"}
        body = json.dumps(payload).encode()
        old_ts = str(int(time.time()) - 400)
        sig = self._sign(secret, body, old_ts)
        with pytest.raises(ExternalServiceError):
            verify_ekyc_webhook(secret, body, sig, old_ts, tolerance_seconds=300)


class TestEkycLiveClientTokenCache:
    def test_token_cache_uses_existing_token(self, monkeypatch):
        client = EkycLiveClient("http://localhost:9999", "cid", "csecret")
        client._token = "cached"
        client._token_expiry = time.time() + 3600
        # No HTTP call should happen
        assert client._access_token() == "cached"


# ---------------------------------------------------------------------------
# Parcours eKYC ↔ souscription (service)
# ---------------------------------------------------------------------------
from app.core.config import settings  # noqa: E402
from app.core.enums import StatutSouscription  # noqa: E402
from app.integrations.ekyc.schemas import EkycResultResponse  # noqa: E402
from app.models.ekyc_session import EkycSession  # noqa: E402
from app.services import ekyc_service  # noqa: E402
from app.services.subscription_decision_service import SubscriptionDecisionEngine  # noqa: E402
from app.tests.test_subscription_cleanup import _sous  # noqa: E402

_STATUS_EVENT = {
    "VERIFIED": "KYC_VERIFIED",
    "REVIEW": "KYC_REVIEW_REQUIRED",
    "REJECTED": "KYC_REJECTED",
}


class _FakeClient:
    def __init__(self, status):
        self.status = status

    def get_result(self, session_id):
        return EkycResultResponse(session_id=session_id, flow="TRAVEL_INSURANCE", status=self.status)


def _webhook(db, monkeypatch, session_id, status):
    monkeypatch.setattr(settings, "EKYC_WEBHOOK_SECRET", "s")
    monkeypatch.setattr(ekyc_service, "get_ekyc_client", lambda: _FakeClient(status))
    body = json.dumps(
        {"event": _STATUS_EVENT[status], "session_id": session_id, "status": status}
    ).encode()
    ts = str(int(time.time()))
    sig = "sha256=" + hmac.new(b"s", ts.encode() + b"." + body, hashlib.sha256).hexdigest()
    return ekyc_service.handle_webhook(
        db, {"X-EKYC-Signature": sig, "X-EKYC-Timestamp": ts}, body
    )


def _approved_sous(db, user, product, monkeypatch, session_id, with_trip=False):
    monkeypatch.setattr(
        SubscriptionDecisionEngine, "_notify_client_outcome", staticmethod(lambda *a, **k: None)
    )
    sous = _sous(db, user, product, start_offset_days=10, statut=StatutSouscription.EN_ATTENTE_PAIEMENT)
    sous.validation_medicale = sous.validation_technique = sous.validation_finale = "approved"
    db.add(EkycSession(
        session_id=session_id, customer_reference=session_id, user_id=user.id,
        souscription_id=sous.id, status="CREATED",
    ))
    db.commit()
    return sous


class TestEkycSubscriptionFlow:
    def test_stub_session_creation_with_return_url(self, db, test_user, monkeypatch):
        monkeypatch.setattr(settings, "EKYC_SERVICE_MODE", "stub")
        session = ekyc_service.create_session(db, user=test_user)
        assert session.status == "CREATED"

    def test_mobile_return_url_is_https_bridge(self, db, test_user, monkeypatch):
        """L'eKYC n'accepte qu'une return_url http(s) : le mobile passe par la
        page relais qui rouvre l'app."""
        captured = {}

        class _Client:
            def create_session(self, **kwargs):
                captured.update(kwargs)
                from app.integrations.ekyc import EkycStubClient
                return EkycStubClient().create_session(**kwargs)

        monkeypatch.setattr(settings, "FRONTEND_BASE_URL", "https://front.example")
        monkeypatch.setattr(ekyc_service, "get_ekyc_client", lambda: _Client())
        ekyc_service.create_session(db, user=test_user, mobile=True)
        assert captured["return_url"] == "https://front.example/ekyc-return.html"

    def test_verdict_change_webhook_is_processed(self, db, test_user, test_product, monkeypatch):
        _approved_sous(db, test_user, test_product, monkeypatch, "K-CHG")
        _webhook(db, monkeypatch, "K-CHG", "REVIEW")
        session = _webhook(db, monkeypatch, "K-CHG", "VERIFIED")
        assert session.status == "VERIFIED"

    def test_retry_verified_after_review_returns_to_payment(
        self, db, test_user, test_product, monkeypatch
    ):
        sous = _approved_sous(db, test_user, test_product, monkeypatch, "K-R1")
        _webhook(db, monkeypatch, "K-R1", "REVIEW")
        assert sous.statut == StatutSouscription.EN_ATTENTE_VALIDATION
        db.add(EkycSession(
            session_id="K-R2", customer_reference="K-R2", user_id=test_user.id,
            souscription_id=sous.id, status="CREATED",
        ))
        db.commit()
        _webhook(db, monkeypatch, "K-R2", "VERIFIED")
        db.refresh(sous)
        assert sous.statut == StatutSouscription.EN_ATTENTE_PAIEMENT

    def test_production_approval_clears_failed_ekyc(self, db, test_user, test_product, monkeypatch):
        sous = _approved_sous(db, test_user, test_product, monkeypatch, "K-REJ")
        _webhook(db, monkeypatch, "K-REJ", "REJECTED")
        assert ekyc_service.identity_cleared(db, sous)[0] is False
        SubscriptionDecisionEngine.record_review(db, sous, "production", True, test_user.id)
        db.commit()
        assert sous.statut == StatutSouscription.EN_ATTENTE_PAIEMENT
        assert ekyc_service.identity_cleared(db, sous)[0] is True

    def test_refresh_session_persists_and_applies_verdict(
        self, db, test_user, test_product, monkeypatch
    ):
        sous = _approved_sous(db, test_user, test_product, monkeypatch, "K-POLL")
        monkeypatch.setattr(ekyc_service, "get_ekyc_client", lambda: _FakeClient("VERIFIED"))
        session = db.query(EkycSession).filter_by(session_id="K-POLL").one()
        ekyc_service.refresh_session(db, session)
        db.rollback()
        db.refresh(session)
        assert session.status == "VERIFIED"
        assert ekyc_service.identity_cleared(db, sous)[0] is True
