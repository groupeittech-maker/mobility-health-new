"""Client HTTP vers IT-TECH eKYC (OAuth2 client_credentials + webhooks)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict

import httpx

from app.integrations.base import BaseServiceClient, ExternalServiceError
from app.integrations.ekyc.schemas import (
    EkycResultResponse,
    EkycSealRequest,
    EkycSealResponse,
    EkycSessionRequest,
    EkycSessionResponse,
    EkycWebhookPayload,
)


class EkycLiveClient(BaseServiceClient):
    """Client synchrone pour l'API eKYC.

    Gère automatiquement l'acquisition et le rafraîchissement du jeton
    OAuth2 ``client_credentials``. Le ``api_key`` hérité de BaseServiceClient
    sert de ``client_id`` ; ``client_secret`` est passé explicitement.
    """

    service_name = "ekyc"

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        api_secret: str = "",
        timeout: float = 30.0,
    ):
        super().__init__(base_url, api_key, timeout)
        self.client_id = api_key
        self.client_secret = api_secret
        self._token: str | None = None
        self._token_expiry: float = 0.0

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 30:
            return self._token
        if not self.base_url or not self.client_id or not self.client_secret:
            raise ExternalServiceError(
                self.service_name,
                "client_id / client_secret eKYC non configurés",
            )
        url = f"{self.base_url}/v1/oauth/token"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    json={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise ExternalServiceError(
                self.service_name,
                exc.response.text or str(exc),
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalServiceError(self.service_name, str(exc)) from exc

        self._token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        self._token_expiry = time.time() + expires_in
        return self._token

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        token = self._access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def create_session(
        self,
        customer_reference: str,
        flow: str,
        metadata: Dict[str, Any] | None = None,
    ) -> EkycSessionResponse:
        payload = EkycSessionRequest(
            customer_reference=customer_reference,
            flow=flow,
            metadata=metadata,
        ).model_dump(mode="json", exclude_none=True)
        data = self._request("POST", "/v1/kyc/sessions", json=payload)
        return EkycSessionResponse.model_validate(data)

    def get_result(self, session_id: str) -> EkycResultResponse:
        data = self._request("GET", f"/v1/kyc/sessions/{session_id}")
        return EkycResultResponse.model_validate(data)

    def seal_document(
        self,
        session_id: str,
        document_reference: str,
        title: str | None = None,
        fields: Dict[str, Any] | None = None,
        pdf_base64: str | None = None,
    ) -> EkycSealResponse:
        payload = EkycSealRequest(
            document_reference=document_reference,
            title=title,
            fields=fields,
            pdf_base64=pdf_base64,
        ).model_dump(mode="json", exclude_none=True)
        data = self._request("POST", f"/v1/kyc/sessions/{session_id}/documents", json=payload)
        return EkycSealResponse.model_validate(data)


def _constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def verify_ekyc_webhook(
    secret: str,
    body: bytes,
    signature_header: str | None,
    timestamp_header: str | None,
    *,
    tolerance_seconds: int = 300,
) -> EkycWebhookPayload:
    """Vérifie la signature HMAC d'un webhook eKYC.

    Format attendu : ``X-EKYC-Signature: sha256=<hmac>`` avec
    ``X-EKYC-Timestamp`` (timestamp UNIX).

    La signature est calculée par eKYC comme :
        HMAC_SHA256(secret, timestamp + "." + body)
    """
    if not secret or not signature_header or not timestamp_header:
        raise ExternalServiceError("ekyc-webhook", "Signature ou timestamp manquant")

    try:
        ts = int(timestamp_header)
    except ValueError as exc:
        raise ExternalServiceError("ekyc-webhook", "Timestamp invalide") from exc

    if tolerance_seconds and abs(int(time.time()) - ts) > tolerance_seconds:
        raise ExternalServiceError("ekyc-webhook", "Timestamp hors tolérance (replay ?)")

    provided = (
        signature_header.split("=", 1)[-1] if "=" in signature_header else signature_header
    )
    expected = hmac.new(
        secret.encode(),
        timestamp_header.encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()

    if not _constant_time_compare(provided, expected):
        raise ExternalServiceError("ekyc-webhook", "Signature invalide")

    return EkycWebhookPayload.model_validate_json(body)


def extract_ekyc_webhook_headers(headers: Dict[str, str]) -> tuple[str | None, str | None]:
    """Extrait les headers eKYC d'une requête (clés insensibles à la casse)."""
    signature = None
    timestamp = None
    for key, value in headers.items():
        lower = key.lower()
        if lower == "x-ekyc-signature":
            signature = value
        elif lower == "x-ekyc-timestamp":
            timestamp = value
    return signature, timestamp
