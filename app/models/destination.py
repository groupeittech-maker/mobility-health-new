from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class DestinationCountry(Base, TimestampMixin):
    """Modèle pour les pays de destination pris en charge"""
    __tablename__ = "destination_countries"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)  # Code ISO ou code personnalisé
    nom = Column(String(200), nullable=False, index=True)
    est_actif = Column(Boolean, default=True, nullable=False)
    ordre_affichage = Column(Integer, default=0, nullable=False)  # Pour ordonner l'affichage
    notes = Column(String(500), nullable=True)
    
    # Relations
    villes = relationship("DestinationCity", back_populates="pays", cascade="all, delete-orphan")


class DestinationCity(Base, TimestampMixin):
    """Modèle pour les villes de destination associées aux pays"""
    __tablename__ = "destination_cities"
    
    id = Column(Integer, primary_key=True, index=True)
    pays_id = Column(Integer, ForeignKey("destination_countries.id", ondelete="CASCADE"), nullable=False, index=True)
    nom = Column(String(200), nullable=False, index=True)
    est_actif = Column(Boolean, default=True, nullable=False)
    ordre_affichage = Column(Integer, default=0, nullable=False)
    notes = Column(String(500), nullable=True)
    
    # Relations
    pays = relationship("DestinationCountry", back_populates="villes")

