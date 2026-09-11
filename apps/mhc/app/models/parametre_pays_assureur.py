"""Paramètres tarifaires par pays de l'assureur : frais de services et taxes."""
from sqlalchemy import Column, Integer, Numeric, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class ParametrePaysAssureur(Base, TimestampMixin):
    """Frais de services (%) appliqué par pays d'assureur."""

    __tablename__ = "parametres_pays_assureur"

    id = Column(Integer, primary_key=True, index=True)
    pays_assureur = Column(String(100), nullable=False, unique=True, index=True)
    frais_services_pct = Column(Numeric(5, 2), nullable=False, default=15)
    actif = Column(Boolean, nullable=False, default=True)

    taxes = relationship(
        "TaxePaysAssureur",
        back_populates="parametre",
        cascade="all, delete-orphan",
        lazy="select",
    )


class TaxePaysAssureur(Base, TimestampMixin):
    """Taxe additionnelle (%) appliquée sur la prime d'assurance, par pays d'assureur."""

    __tablename__ = "taxes_pays_assureur"

    id = Column(Integer, primary_key=True, index=True)
    parametre_pays_assureur_id = Column(
        Integer,
        ForeignKey("parametres_pays_assureur.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nom = Column(String(100), nullable=False)
    taux_pct = Column(Numeric(5, 2), nullable=False)
    actif = Column(Boolean, nullable=False, default=True)
    ordre_affichage = Column(Integer, nullable=False, default=0)

    parametre = relationship("ParametrePaysAssureur", back_populates="taxes")
