"""Schémas alignés sur contracts/ocr-api.v1.md."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class OcrExtractRequest(BaseModel):
    document_type: str = Field(..., description="passeport, carte_identite, formulaire, autre")
    file_url: Optional[str] = None
    file_base64: Optional[str] = None
    filename: Optional[str] = None
    language: str = "fra"
    metadata: Optional[Dict[str, Any]] = None


class OcrExtractResponse(BaseModel):
    fields: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    raw_text: Optional[str] = None
    engine: str = "stub"
