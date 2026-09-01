from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class ProjetVoyageDocument(Base, TimestampMixin):
    """Pièces jointes associées à un projet de voyage."""

    __tablename__ = "projet_voyage_documents"

    id = Column(Integer, primary_key=True, index=True)
    projet_voyage_id = Column(
        Integer,
        ForeignKey("projets_voyage.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type = Column(String(50), nullable=False)
    display_name = Column(String(255), nullable=False)
    bucket_name = Column(String(63), nullable=False)
    object_name = Column(String(512), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    minio_etag = Column(String(64), nullable=True)

    projet_voyage = relationship("ProjetVoyage", back_populates="documents")















