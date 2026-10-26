"""Tests unitaires du client Meta WhatsApp Cloud API."""
from __future__ import annotations

from app.integrations.messaging.schemas import MessageSendRequest
from app.integrations.messaging.whatsapp_meta import (
    WhatsAppMetaClient,
    normalize_msisdn,
)


def _client() -> WhatsAppMetaClient:
    return WhatsAppMetaClient(
        access_token="token",
        phone_number_id="123456789",
        api_version="v20.0",
    )


def test_normalize_msisdn_strips_non_digits():
    assert normalize_msisdn("+242 06 123 45 67") == "242061234567"
    assert normalize_msisdn("00225-07070707") == "0022507070707"


def test_build_text_payload():
    req = MessageSendRequest(channel="whatsapp", to="+242061234567", message="Bonjour")
    payload = _client().build_payload(req, "242061234567")
    assert payload["messaging_product"] == "whatsapp"
    assert payload["to"] == "242061234567"
    assert payload["type"] == "text"
    assert payload["text"]["body"] == "Bonjour"
    assert payload["text"]["preview_url"] is False


def test_build_template_payload_with_params():
    req = MessageSendRequest(
        channel="whatsapp",
        to="+242061234567",
        message="ignored",
        template_name="mhc_code_verification",
        template_language="fr",
        template_params=["123456"],
    )
    payload = _client().build_payload(req, "242061234567")
    assert payload["type"] == "template"
    assert payload["template"]["name"] == "mhc_code_verification"
    assert payload["template"]["language"]["code"] == "fr"
    params = payload["template"]["components"][0]["parameters"]
    assert params == [{"type": "text", "text": "123456"}]


def test_send_maps_meta_response(monkeypatch):
    client = _client()
    captured = {}

    def fake_request(method, path, *, json=None, params=None, extra_headers=None):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "242061234567", "wa_id": "242061234567"}],
            "messages": [{"id": "wamid.abc123"}],
        }

    monkeypatch.setattr(client, "_request", fake_request)
    resp = client.send(
        MessageSendRequest(channel="whatsapp", to="+242 06 123 45 67", message="Test")
    )
    assert resp.status == "sent"
    assert resp.channel == "whatsapp"
    assert resp.message_id == "wamid.abc123"
    assert captured["path"] == "/123456789/messages"
    assert captured["json"]["to"] == "242061234567"


def test_send_rejects_sms_channel():
    resp = _client().send(
        MessageSendRequest(channel="sms", to="+242061234567", message="Test")
    )
    assert resp.status == "failed"
    assert "SMS" in resp.details["error"]


def test_send_rejects_empty_destination():
    resp = _client().send(
        MessageSendRequest(channel="whatsapp", to="abc", message="Test")
    )
    assert resp.status == "failed"
