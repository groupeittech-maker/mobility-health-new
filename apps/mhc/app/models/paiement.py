from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from app.core.database import Base
from app.core.enums import StatutPaiement, TypePaiement
from app.models.base import TimestampMixin


class TypePaiementColumn(TypeDecorator):
    """Normalise type_paiement (DB majuscules -> enum minuscules)."""
    impl = String(50)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if hasattr(value, "name"):
            return value.name
        s = str(value).upper().strip()
        for t in TypePaiement:
            if t.name == s:
                return t.name
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        s = str(value).upper().strip()
        if s == "CARTE_CREDIT":
            return TypePaiement.CARTE_BANCAIRE
        for t in TypePaiement:
            if t.name == s:
                return t
        return TypePaiement.CARTE_BANCAIRE


class StatutPaiementColumn(TypeDecorator):
    """Normalise statut paiement (DB majuscules -> enum minuscules)."""
    impl = String(30)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if hasattr(value, "name"):
            return value.name
        s = str(value).upper().strip()
        for st in StatutPaiement:
            if st.name == s:
                return st.name
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        s = str(value).upper().strip()
        # Mapping DB ECHEC -> Python ECHOUE
        if s == "ECHEC":
            return StatutPaiement.ECHOUE
        for st in StatutPaiement:
            if st.name == s:
                return st
        return StatutPaiement.EN_ATTENTE


class Paiement(Base, TimestampMixin):
    """Modèle pour les paiements"""
    __tablename__ = "paiements"
    
    id = Column(Integer, primary_key=True, index=True)
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    montant = Column(Numeric(10, 2), nullable=False)
    type_paiement = Column(TypePaiementColumn, nullable=False)
    statut = Column(StatutPaiementColumn, default=StatutPaiement.EN_ATTENTE, nullable=False)
    date_paiement = Column(DateTime, nullable=True)
    reference_transaction = Column(String(200), unique=True, nullable=True, index=True)
    reference_externe = Column(String(200), nullable=True)  # Référence du système de paiement externe
    notes = Column(Text, nullable=True)
    montant_rembourse = Column(Numeric(10, 2), nullable=True)  # Si remboursement partiel
    
    # Relations
    souscription = relationship("Souscription", back_populates="paiements")
    user = relationship("User", back_populates="paiements")
    attestations = relationship("Attestation", back_populates="paiement", cascade="all, delete-orphan")
