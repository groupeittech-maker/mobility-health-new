from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Rapport(Base, TimestampMixin):
    """Modèle pour les rapports médicaux signés"""
    __tablename__ = "rapports"
    
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    sinistre_id = Column(Integer, ForeignKey("sinistres.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Informations du rapport
    titre = Column(String(200), nullable=False)
    type_rapport = Column(String(50), nullable=False)  # medical, technique, etc.
    contenu = Column(Text, nullable=True)  # Contenu textuel du rapport
    
    # Fichier signé
    fichier_path = Column(String(500), nullable=True)  # Chemin vers le fichier dans Minio
    fichier_nom = Column(String(255), nullable=True)  # Nom original du fichier
    fichier_taille = Column(Integer, nullable=True)  # Taille en bytes
    fichier_type = Column(String(100), nullable=True)  # MIME type
    
    # Signature
    est_signe = Column(Boolean, default=False, nullable=False)
    signe_par = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # ID du médecin qui a signé
    date_signature = Column(DateTime, nullable=True)
    signature_digitale = Column(Text, nullable=True)  # Hash ou signature digitale
    
    # Statut
    statut = Column(String(20), default="draft", nullable=False, index=True)  # draft, signed, validated
    
    # Relations
    hospital = relationship("Hospital", back_populates="rapports")
    sinistre = relationship("Sinistre", back_populates="rapports")
    user = relationship("User", foreign_keys=[user_id], back_populates="rapports")
    signataire = relationship("User", foreign_keys=[signe_par], back_populates="rapports_signed")


















