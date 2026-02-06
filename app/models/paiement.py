from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import StatutPaiement, TypePaiement
from app.models.base import TimestampMixin


class Paiement(Base, TimestampMixin):
    """Modèle pour les paiements"""
    __tablename__ = "paiements"
    
    id = Column(Integer, primary_key=True, index=True)
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    montant = Column(Numeric(10, 2), nullable=False)
    type_paiement = Column(SQLEnum(TypePaiement), nullable=False)
    statut = Column(SQLEnum(StatutPaiement), default=StatutPaiement.EN_ATTENTE, nullable=False)
    date_paiement = Column(DateTime, nullable=True)
    reference_transaction = Column(String(200), unique=True, nullable=True, index=True)
    reference_externe = Column(String(200), nullable=True)  # Référence du système de paiement externe
    notes = Column(Text, nullable=True)
    montant_rembourse = Column(Numeric(10, 2), nullable=True)  # Si remboursement partiel
    
    # Relations
    souscription = relationship("Souscription", back_populates="paiements")
    user = relationship("User", back_populates="paiements")
    attestations = relationship("Attestation", back_populates="paiement", cascade="all, delete-orphan")
