from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Alerte(Base, TimestampMixin):
    """Modèle pour les alertes SOS"""
    __tablename__ = "alertes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    numero_alerte = Column(String(100), unique=True, nullable=False, index=True)
    latitude = Column(Numeric(10, 8), nullable=False)  # Coordonnées GPS
    longitude = Column(Numeric(11, 8), nullable=False)
    adresse = Column(String(500), nullable=True)  # Adresse textuelle si disponible
    description = Column(Text, nullable=True)  # Description de l'urgence
    statut = Column(String(20), default="en_attente", nullable=False, index=True)  # en_attente, en_cours, resolue, annulee
    priorite = Column(String(20), default="normale", nullable=False)  # faible, normale, elevee, critique
    
    # Relations
    user = relationship("User", foreign_keys=[user_id])
    souscription = relationship("Souscription", foreign_keys=[souscription_id])
    sinistres = relationship("Sinistre", back_populates="alerte", cascade="all, delete-orphan")
