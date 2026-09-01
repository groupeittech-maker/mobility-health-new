from sqlalchemy import Column, Integer, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class HistoriquePrix(Base, TimestampMixin):
    """Modèle pour l'historique des prix des produits d'assurance"""
    __tablename__ = "historique_prix"
    
    id = Column(Integer, primary_key=True, index=True)
    produit_assurance_id = Column(Integer, ForeignKey("produits_assurance.id", ondelete="CASCADE"), nullable=False, index=True)
    ancien_prix = Column(Numeric(10, 2), nullable=True)  # Prix avant modification
    nouveau_prix = Column(Numeric(10, 2), nullable=False)  # Nouveau prix
    raison_modification = Column(Text, nullable=True)  # Raison du changement
    modifie_par_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Relations
    produit_assurance = relationship("ProduitAssurance", back_populates="historique_prix")
    modifie_par = relationship("User", foreign_keys=[modifie_par_user_id])
