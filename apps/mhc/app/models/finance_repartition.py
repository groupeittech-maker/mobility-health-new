from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import CleRepartition
from app.models.base import TimestampMixin


class Repartition(Base, TimestampMixin):
    """Modèle pour les répartitions financières"""
    __tablename__ = "finance_repartitions"
    
    id = Column(Integer, primary_key=True, index=True)
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    paiement_id = Column(Integer, ForeignKey("paiements.id", ondelete="CASCADE"), nullable=False, index=True)
    produit_assurance_id = Column(Integer, ForeignKey("produits_assurance.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    montant_total = Column(Numeric(12, 2), nullable=False)
    cle_repartition = Column(String(50), nullable=False)  # CleRepartition enum value
    
    # Détails de la répartition (JSON)
    repartition_details = Column(JSON, nullable=True)  # {"account_id": amount, ...}
    
    # Calculs
    montant_par_personne = Column(Numeric(12, 2), nullable=True)
    montant_par_groupe = Column(Numeric(12, 2), nullable=True)
    montant_par_duree = Column(Numeric(12, 2), nullable=True)
    montant_par_destination = Column(Numeric(12, 2), nullable=True)
    montant_fixe = Column(Numeric(12, 2), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    # Relations
    souscription = relationship("Souscription", backref="repartitions")
    paiement = relationship("Paiement", backref="repartitions")
    produit_assurance = relationship("ProduitAssurance", backref="repartitions")


















