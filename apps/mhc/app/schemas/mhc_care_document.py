from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MhcCareDocumentIssueRequest(BaseModel):
    document_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class MhcCareDocumentResponse(BaseModel):
    id: int
    sinistre_id: int
    document_type: str
    titre: str
    numero: str
    statut: str
    issued_at: datetime
    valid_until: Optional[datetime] = None
    issued_by_id: Optional[int] = None
    parent_document_id: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MhcCareDocumentListResponse(BaseModel):
    sinistre_id: int
    numero_sinistre: Optional[str] = None
    dossier_ouvert: bool
    actions_possibles: List[str] = []
    documents: List[MhcCareDocumentResponse] = []
