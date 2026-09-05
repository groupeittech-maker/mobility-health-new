from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin

ATTACHMENT_CERTIFICAT_DECES = "certificat_deces"


class SinistreAttachment(Base, TimestampMixin):
    """Pièce jointe rattachée à un dossier sinistre (ex. certificat de décès hospitalier)."""

    __tablename__ = "sinistre_attachments"
    __table_args__ = (
        UniqueConstraint("sinistre_id", "attachment_type", name="uq_sinistre_attachment_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    sinistre_id = Column(Integer, ForeignKey("sinistres.id", ondelete="CASCADE"), nullable=False, index=True)
    attachment_type = Column(String(50), nullable=False, index=True)
    bucket_name = Column(String(120), nullable=False)
    object_name = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    sinistre = relationship("Sinistre", back_populates="attachments")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
