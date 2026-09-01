from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class ValidationAttestation(Base, TimestampMixin):
    """Modèle pour les validations d'attestation (médecin, technique, production)"""
    __tablename__ = "validations_attestation"
    
    id = Column(Integer, primary_key=True, index=True)
    attestation_id = Column(Integer, ForeignKey("attestations.id", ondelete="CASCADE"), nullable=False, index=True)
    type_validation = Column(String(20), nullable=False, index=True)  # 'medecin', 'technique', 'production'
    valide_par_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    est_valide = Column(Boolean, default=False, nullable=False)
    date_validation = Column(DateTime, nullable=True)
    commentaires = Column(Text, nullable=True)
    
    # Relations
    attestation = relationship("Attestation", back_populates="validations")
    valide_par = relationship("User", foreign_keys=[valide_par_user_id])

