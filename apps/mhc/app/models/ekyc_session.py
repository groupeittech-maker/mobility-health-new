"""Persistance locale des sessions eKYC IT-TECH.

Permet à MHC de retrouver l'utilisateur/la souscription associés à une session,
de stocker le résultat minimisé et d'empêcher les traitements en double des webhooks.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class EkycSession(Base, TimestampMixin):
    __tablename__ = "ekyc_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(120), unique=True, nullable=False, index=True)
    customer_reference = Column(String(120), nullable=False, index=True)

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    souscription_id = Column(
        Integer, ForeignKey("souscriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    flow = Column(String(40), nullable=False, default="TRAVEL_INSURANCE")
    status = Column(String(20), nullable=False, default="CREATED", index=True)
    verification_url = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Données minimisées renvoyées par eKYC
    identity = Column(JSON, nullable=True)
    checks = Column(JSON, nullable=True)
    reasons = Column(JSON, nullable=True)

    webhook_received_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="ekyc_sessions")
    souscription = relationship("Souscription", back_populates="ekyc_sessions")
