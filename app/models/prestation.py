from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Prestation(Base, TimestampMixin):
    """Modèle pour les prestations médicales d'un hôpital"""
    __tablename__ = "prestations"
    
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    sinistre_id = Column(Integer, ForeignKey("sinistres.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Informations de la prestation
    code_prestation = Column(String(50), nullable=False, index=True)  # Code de la prestation (ex: CONSULT, RADIO, etc.)
    libelle = Column(String(200), nullable=False)  # Libellé de la prestation
    description = Column(Text, nullable=True)
    
    # Montants
    montant_unitaire = Column(Numeric(10, 2), nullable=False)
    quantite = Column(Integer, default=1, nullable=False)
    montant_total = Column(Numeric(10, 2), nullable=False)  # montant_unitaire * quantite
    
    # Dates
    date_prestation = Column(DateTime, nullable=False)
    
    # Statut
    statut = Column(String(20), default="pending", nullable=False, index=True)  # pending, validated, invoiced
    
    # Relations
    hospital = relationship("Hospital", back_populates="prestations")
    sinistre = relationship("Sinistre", back_populates="prestations")
    user = relationship("User", back_populates="prestations")
    invoice_items = relationship("InvoiceItem", back_populates="prestation")


















