"""Client HTTP de base pour les services externes IT-Tech."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0


class ExternalServiceError(Exception):
    """Erreur lors d'un appel à un service externe."""

    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        self.service = service
        self.status_code = status_code
        super().__init__(f"[{service}] {message}")


class BaseServiceClient:
    """Client HTTP minimal avec authentification par clé API."""

    service_name: str = "external"

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.base_url:
            raise ExternalServiceError(
                self.service_name,
                "URL du service non configurée",
            )
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=json,
                    params=params,
                )
                response.raise_for_status()
                if response.content:
                    return response.json()
                return {}
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "%s HTTP %s: %s",
                self.service_name,
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise ExternalServiceError(
                self.service_name,
                exc.response.text or str(exc),
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("%s request error: %s", self.service_name, exc)
            raise ExternalServiceError(self.service_name, str(exc)) from exc
