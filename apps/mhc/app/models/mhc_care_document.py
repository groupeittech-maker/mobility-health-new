from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class MhcCareDocument(Base, TimestampMixin):
    """Bon ou attestation du parcours de prise en charge d'urgence MHC."""

    __tablename__ = "mhc_care_documents"

    id = Column(Integer, primary_key=True, index=True)
    sinistre_id = Column(Integer, ForeignKey("sinistres.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(20), nullable=False, index=True)
    numero = Column(String(120), unique=True, nullable=False, index=True)
    statut = Column(String(20), nullable=False, default="emi", index=True)
    issued_at = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=True, index=True)
    issued_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_document_id = Column(Integer, ForeignKey("mhc_care_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    payload = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    sinistre = relationship("Sinistre", back_populates="care_documents")
    issued_by = relationship("User", foreign_keys=[issued_by_id])
    parent_document = relationship("MhcCareDocument", remote_side=[id], foreign_keys=[parent_document_id])
