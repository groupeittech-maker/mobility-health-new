from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Questionnaire(Base, TimestampMixin):
    """Modèle pour les questionnaires (court et long)"""
    __tablename__ = "questionnaires"
    
    id = Column(Integer, primary_key=True, index=True)
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    type_questionnaire = Column(String(20), nullable=False, index=True)  # 'short' ou 'long'
    version = Column(Integer, default=1, nullable=False)  # Version du questionnaire
    reponses = Column(JSON, nullable=False)  # Stockage des réponses en JSON
    statut = Column(String(20), default="en_attente", nullable=False)  # en_attente, complete, archive
    notes = Column(Text, nullable=True)
    
    # Relations
    souscription = relationship("Souscription", back_populates="questionnaires")
    ia_analyses = relationship("IAAnalysis", back_populates="questionnaire", cascade="all, delete-orphan")

