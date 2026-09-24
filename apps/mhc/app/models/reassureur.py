from sqlalchemy import Column, Integer, String, Boolean, Numeric
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Reassureur(Base, TimestampMixin):
    """Entité réassureur (compte partenaire en consultation côté réassureur)."""

    __tablename__ = "reassureurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False, index=True)
    code = Column(String(50), nullable=True, unique=True, index=True)
    pays = Column(String(100), nullable=True)
    ville = Column(String(100), nullable=True)
    adresse = Column(String(500), nullable=True)
    telephone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    contact_nom = Column(String(200), nullable=True)
    est_actif = Column(Boolean, nullable=False, default=True)
    # Paramètres par défaut réutilisables sur les produits
    cession_defaut_pct = Column(Numeric(5, 2), nullable=True)
    commission_cession_defaut_pct = Column(Numeric(5, 2), nullable=True)

    produits = relationship("ProduitAssurance", back_populates="reassureur")


class ProduitSurprime(Base, TimestampMixin):
    """Surprime produit par tranche d'âge (maquette tarification — table)."""

    __tablename__ = "produit_surprimes"

    id = Column(Integer, primary_key=True, index=True)
    produit_id = Column(Integer, nullable=False, index=True)
    age_min = Column(Integer, nullable=False)
    age_max = Column(Integer, nullable=False)
    taux_pct = Column(Numeric(6, 2), nullable=False, default=0)
    montant_fixe = Column(Numeric(10, 2), nullable=True)
    formule = Column(String(50), nullable=True)  # ex: "pourcentage", "montant_fixe"
