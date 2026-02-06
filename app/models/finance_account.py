from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import Role
from app.models.base import TimestampMixin


class Account(Base, TimestampMixin):
    """Modèle pour les comptes financiers"""
    __tablename__ = "finance_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(50), unique=True, nullable=False, index=True)
    account_name = Column(String(200), nullable=False)
    account_type = Column(String(50), nullable=False)  # client, provider, internal, etc.
    balance = Column(Numeric(12, 2), default=0, nullable=False)
    currency = Column(String(3), default="EUR", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Relations
    owner = relationship("User", backref="finance_accounts")
    movements = relationship("Movement", back_populates="account", cascade="all, delete-orphan")


















