from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Text, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Movement(Base, TimestampMixin):
    """Modèle pour les mouvements financiers (journal)"""
    __tablename__ = "finance_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("finance_accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    movement_type = Column(String(50), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="EUR", nullable=False)
    description = Column(Text, nullable=True)
    reference = Column(String(200), nullable=True, index=True)  # Référence unique pour anti-doublon
    reference_type = Column(String(50), nullable=True)  # payment_id, subscription_id, etc.
    related_id = Column(Integer, nullable=True, index=True)  # ID de l'entité liée
    
    # Relations
    account = relationship("Account", back_populates="movements")
    
    # Index unique pour anti-doublon (créé dans la migration)

