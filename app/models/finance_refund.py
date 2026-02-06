from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Refund(Base, TimestampMixin):
    """Modèle pour les remboursements"""
    __tablename__ = "finance_refunds"
    
    id = Column(Integer, primary_key=True, index=True)
    paiement_id = Column(Integer, ForeignKey("paiements.id", ondelete="RESTRICT"), nullable=False, index=True)
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="RESTRICT"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("finance_accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    montant = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="EUR", nullable=False)
    statut = Column(String(20), default="pending", nullable=False, index=True)
    
    raison = Column(Text, nullable=False)  # Raison du remboursement
    reference_remboursement = Column(String(200), unique=True, nullable=True, index=True)
    
    date_remboursement = Column(DateTime, nullable=True)
    processed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relations
    paiement = relationship("Paiement", backref="refunds")
    souscription = relationship("Souscription", backref="refunds")
    account = relationship("Account", backref="refunds")
    processor = relationship("User", backref="processed_refunds")

