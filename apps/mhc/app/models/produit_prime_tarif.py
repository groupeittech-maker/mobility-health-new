"""Modèle pour les tarifs de prime par durée, zone et âge."""
from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class ProduitPrimeTarif(Base, TimestampMixin):
    """
    Tarif de prime pour un produit selon durée, zone et âge.
    """
    __tablename__ = "produit_prime_tarif"

    id = Column(Integer, primary_key=True, index=True)
    produit_assurance_id = Column(
        Integer,
        ForeignKey("produits_assurance.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    duree_min_jours = Column(Integer, nullable=False)
    duree_max_jours = Column(Integer, nullable=False)
    zone_code = Column(String(50), nullable=True, index=True)
    destination_country_id = Column(
        Integer,
        ForeignKey("destination_countries.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    age_min = Column(Integer, nullable=True)
    age_max = Column(Integer, nullable=True)
    prix = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=True, default="XAF")
    ordre_priorite = Column(Integer, default=0, nullable=False)

    produit_assurance = relationship("ProduitAssurance", back_populates="prime_tarifs")
    destination_country = relationship("DestinationCountry", backref="prime_tarifs")
