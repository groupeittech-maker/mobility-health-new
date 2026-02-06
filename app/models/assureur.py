from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Assureur(Base, TimestampMixin):
    """Modèle représentant un assureur partenaire."""

    __tablename__ = "assureurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False, unique=True)
    pays = Column(String(100), nullable=False)
    logo_url = Column(String(500), nullable=True)
    adresse = Column(String(255), nullable=True)
    telephone = Column(String(50), nullable=True)
    agent_comptable_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    agent_comptable = relationship(
        "User",
        back_populates="assureurs_comptables",
        foreign_keys=[agent_comptable_id],
    )
    produits_assurance = relationship("ProduitAssurance", back_populates="assureur_obj")
    agents = relationship("AssureurAgent", back_populates="assureur", cascade="all, delete-orphan", lazy="select")
    ia_analyses = relationship("IAAnalysisAssureur", back_populates="assureur", cascade="all, delete-orphan")


