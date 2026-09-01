"""Intégration OCR/HTR Service (phase 2 — stub délègue à ia_module)."""
from __future__ import annotations

from typing import Literal, Protocol

from app.core.config import settings
from app.integrations.ocr.schemas import OcrExtractRequest, OcrExtractResponse
from app.integrations.ocr.stub import OcrStubClient


class OcrClient(Protocol):
    def extract(self, request: OcrExtractRequest) -> OcrExtractResponse: ...


def get_ocr_client() -> OcrClient:
    mode: Literal["stub", "live"] = settings.OCR_SERVICE_MODE  # type: ignore[assignment]
    if mode == "live":
        from app.integrations.ocr.client import OcrLiveClient

        return OcrLiveClient(
            base_url=settings.OCR_SERVICE_URL,
            api_key=settings.OCR_SERVICE_API_KEY,
        )
    return OcrStubClient()
