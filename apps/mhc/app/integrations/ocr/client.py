"""Client HTTP vers le service OCR/HTR."""
from __future__ import annotations

from app.integrations.base import BaseServiceClient
from app.integrations.ocr.schemas import OcrExtractRequest, OcrExtractResponse


class OcrLiveClient(BaseServiceClient):
    service_name = "ocr"

    def extract(self, request: OcrExtractRequest) -> OcrExtractResponse:
        payload = request.model_dump(mode="json", exclude_none=True)
        data = self._request("POST", "/v1/ocr/extract", json=payload)
        return OcrExtractResponse.model_validate(data)
