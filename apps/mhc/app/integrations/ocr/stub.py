"""Stub OCR — délègue au module ia_module local (Tesseract) en attendant le service externe."""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict

from app.integrations.ocr.schemas import OcrExtractRequest, OcrExtractResponse

logger = logging.getLogger(__name__)


class OcrStubClient:
    def extract(self, request: OcrExtractRequest) -> OcrExtractResponse:
        try:
            from app.ia_module import analyser_document

            path = self._materialize_file(request)
            if not path:
                return OcrExtractResponse(fields={}, confidence=0.0, engine="stub")
            result = analyser_document(path, request.document_type)
            fields: Dict[str, Any] = {}
            confidence = 0.0
            raw_text = None
            if isinstance(result, dict):
                fields = result.get("champs") or result.get("fields") or result
                confidence = float(result.get("confidence") or result.get("score") or 0.0)
                raw_text = result.get("texte_brut") or result.get("raw_text")
            return OcrExtractResponse(
                fields=fields if isinstance(fields, dict) else {},
                confidence=confidence,
                raw_text=raw_text,
                engine="ia_module_tesseract",
            )
        except Exception as exc:
            logger.warning("OCR stub (ia_module): %s", exc)
            return OcrExtractResponse(fields={}, confidence=0.0, engine="stub_error")

    def _materialize_file(self, request: OcrExtractRequest) -> str | None:
        if request.file_url and request.file_url.startswith("/"):
            return request.file_url if os.path.isfile(request.file_url) else None
        if request.file_base64:
            import base64

            raw = base64.b64decode(request.file_base64)
            suffix = os.path.splitext(request.filename or "doc.pdf")[1] or ".pdf"
            fd, path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            with open(path, "wb") as f:
                f.write(raw)
            return path
        return None
