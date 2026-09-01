from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class HospitalStay(Base, TimestampMixin):
    """Séjour hospitalier déclenché suite à un sinistre."""

    __tablename__ = "hospital_stays"

    id = Column(Integer, primary_key=True, index=True)
    sinistre_id = Column(Integer, ForeignKey("sinistres.id", ondelete="CASCADE"), nullable=False, unique=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_doctor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status = Column(String(20), default="in_progress", nullable=False, index=True)
    report_status = Column(String(30), default="draft", nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    orientation_notes = Column(Text, nullable=True)

    report_motif_consultation = Column(Text, nullable=True)
    report_motif_hospitalisation = Column(Text, nullable=True)
    report_duree_sejour_heures = Column(Integer, nullable=True)
    report_actes = Column(JSON, nullable=True)
    report_examens = Column(JSON, nullable=True)
    report_resume = Column(Text, nullable=True)
    report_observations = Column(Text, nullable=True)
    report_submitted_at = Column(DateTime, nullable=True)
    report_submitted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    validated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    validation_notes = Column(Text, nullable=True)

    # Relationships
    sinistre = relationship("Sinistre", back_populates="hospital_stay")
    hospital = relationship("Hospital", back_populates="hospital_stays")
    patient = relationship("User", foreign_keys=[patient_id])
    assigned_doctor = relationship("User", foreign_keys=[assigned_doctor_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    report_author = relationship("User", foreign_keys=[report_submitted_by])
    validated_by = relationship("User", foreign_keys=[validated_by_id])
    invoice = relationship("Invoice", back_populates="hospital_stay", uselist=False)