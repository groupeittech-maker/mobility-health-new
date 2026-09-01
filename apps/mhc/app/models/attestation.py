from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Attestation(Base, TimestampMixin):
    """Modèle pour les attestations (provisoires et définitives)"""
    __tablename__ = "attestations"
    
    id = Column(Integer, primary_key=True, index=True)
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    paiement_id = Column(Integer, ForeignKey("paiements.id", ondelete="SET NULL"), nullable=True, index=True)
    type_attestation = Column(String(20), nullable=False, index=True)  # 'provisoire' ou 'definitive'
    numero_attestation = Column(String(100), unique=True, nullable=False, index=True)
    chemin_fichier_minio = Column(String(500), nullable=False)  # Chemin dans Minio
    bucket_minio = Column(String(100), default="attestations", nullable=False)
    url_signee = Column(Text, nullable=True)  # URL signée temporaire
    date_expiration_url = Column(DateTime, nullable=True)  # Date d'expiration de l'URL signée
    carte_numerique_path = Column(String(500), nullable=True)
    carte_numerique_bucket = Column(String(100), nullable=True)
    carte_numerique_url = Column(Text, nullable=True)
    carte_numerique_expires_at = Column(DateTime, nullable=True)
    est_valide = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relations
    souscription = relationship("Souscription", back_populates="attestations")
    paiement = relationship("Paiement", back_populates="attestations")
    validations = relationship("ValidationAttestation", back_populates="attestation", cascade="all, delete-orphan")

