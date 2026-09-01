from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Sinistre(Base, TimestampMixin):
    """Modèle pour les sinistres"""
    __tablename__ = "sinistres"
    
    id = Column(Integer, primary_key=True, index=True)
    alerte_id = Column(Integer, ForeignKey("alertes.id", ondelete="CASCADE"), nullable=False, index=True)
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True)
    numero_sinistre = Column(String(100), unique=True, nullable=True, index=True)
    description = Column(Text, nullable=True)
    statut = Column(String(20), default="en_cours", nullable=False, index=True)  # en_cours, resolu, annule
    agent_sinistre_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    medecin_referent_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    
    # Relations
    alerte = relationship("Alerte", back_populates="sinistres")
    souscription = relationship("Souscription", foreign_keys=[souscription_id])
    hospital = relationship("Hospital", foreign_keys=[hospital_id], back_populates="sinistres")
    agent_sinistre = relationship("User", foreign_keys=[agent_sinistre_id])
    medecin_referent = relationship("User", foreign_keys=[medecin_referent_id])
    prestations = relationship("Prestation", back_populates="sinistre", cascade="all, delete-orphan")
    rapports = relationship("Rapport", back_populates="sinistre", cascade="all, delete-orphan")
    workflow_steps = relationship(
        "SinistreProcessStep",
        back_populates="sinistre",
        cascade="all, delete-orphan",
        order_by="SinistreProcessStep.ordre",
    )
    hospital_stay = relationship(
        "HospitalStay",
        back_populates="sinistre",
        uselist=False,
        cascade="all, delete-orphan"
    )
