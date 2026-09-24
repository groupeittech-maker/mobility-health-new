"""Workflows médicaux : rapports d'étape et double validation MC → Affaires médicales."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class HospitalMedicalReport(Base):
    """Rapport médical d'un séjour : 'etape' (N possibles) ou 'final'."""

    __tablename__ = "hospital_medical_reports"

    id = Column(Integer, primary_key=True, index=True)
    stay_id = Column(Integer, ForeignKey("hospital_stays.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = Column(String(20), nullable=False, default="etape", index=True)  # etape | final
    resume = Column(Text, nullable=True)
    actes = Column(JSON, nullable=True)
    examens = Column(JSON, nullable=True)
    observations = Column(Text, nullable=True)
    evolution = Column(String(50), nullable=True)  # favorable | stationnaire | defavorable
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Double validation : 1re médecin-conseil, 2e affaires médicales.
    statut = Column(String(20), nullable=False, default="soumis", index=True)  # soumis | validee_mc | validee_am | refusee
    validated_mc_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validated_mc_at = Column(DateTime, nullable=True)
    validated_am_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validated_am_at = Column(DateTime, nullable=True)
    refusal_reason = Column(Text, nullable=True)
    escalated = Column(Boolean, nullable=False, default=False)  # reprise par les affaires médicales (2e possibilité)

    stay = relationship("HospitalStay", foreign_keys=[stay_id])
