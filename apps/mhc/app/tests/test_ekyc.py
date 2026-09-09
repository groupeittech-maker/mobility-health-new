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
