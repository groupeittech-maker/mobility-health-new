from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class TransactionLog(Base, TimestampMixin):
    """Modèle pour logger les transactions de paiement"""
    __tablename__ = "transaction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("paiements.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # payment_initiated, payment_success, etc.
    details = Column(JSON, nullable=True)  # Détails de la transaction en JSON
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relations
    payment = relationship("Paiement", backref="transaction_logs")
    user = relationship("User", backref="transaction_logs")


















