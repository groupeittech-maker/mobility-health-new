from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from app.core.database import Base
from app.core.enums import StatutSouscription
from app.models.base import TimestampMixin


class StatutSouscriptionColumn(TypeDecorator):
    """Colonne statut qui envoie toujours la valeur en minuscules vers la BDD (compatible enum PostgreSQL)."""
    impl = String(30)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if hasattr(value, "value"):
            return value.value
        return str(value).lower() if value else None

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        s = str(value).lower().strip()
        for st in StatutSouscription:
            if st.value == s:
                return st
        return StatutSouscription.EN_ATTENTE


class Souscription(Base, TimestampMixin):
    """Modèle pour les souscriptions d'assurance"""
    __tablename__ = "souscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    produit_assurance_id = Column(Integer, ForeignKey("produits_assurance.id", ondelete="RESTRICT"), nullable=False, index=True)
    projet_voyage_id = Column(Integer, ForeignKey("projets_voyage.id", ondelete="SET NULL"), nullable=True, index=True)
    numero_souscription = Column(String(100), unique=True, nullable=False, index=True)
    prix_applique = Column(Numeric(10, 2), nullable=False)  # Prix final appliqué à la souscription
    prime_assurance = Column(Numeric(12, 2), nullable=True)  # Prime + surprime (grille voyage)
    frais_services = Column(Numeric(12, 2), nullable=True)  # Frais de services (grille voyage)
    canal_distribution = Column(String(20), nullable=False, default="assureur")  # assureur | courtier
    courtier_id = Column(Integer, ForeignKey("courtiers.id", ondelete="SET NULL"), nullable=True, index=True)
    date_debut = Column(DateTime, nullable=False)
    date_fin = Column(DateTime, nullable=True)
    statut = Column(StatutSouscriptionColumn, default=StatutSouscription.EN_ATTENTE, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Validations
    validation_medicale = Column(String(20), nullable=True, index=True)  # pending, approved, rejected
    validation_medicale_par = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validation_medicale_date = Column(DateTime, nullable=True)
    validation_medicale_notes = Column(Text, nullable=True)
    
    validation_technique = Column(String(20), nullable=True, index=True)  # pending, approved, rejected
    validation_technique_par = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validation_technique_date = Column(DateTime, nullable=True)
    validation_technique_notes = Column(Text, nullable=True)
    
    validation_finale = Column(String(20), nullable=True, index=True)  # pending, approved, rejected
    validation_finale_par = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validation_finale_date = Column(DateTime, nullable=True)
    validation_finale_notes = Column(Text, nullable=True)
    
    # Résiliation
    demande_resiliation = Column(String(20), nullable=True, index=True)  # pending, approved, rejected
    demande_resiliation_date = Column(DateTime, nullable=True)
    demande_resiliation_notes = Column(Text, nullable=True)
    demande_resiliation_par_agent = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    demande_resiliation_date_traitement = Column(DateTime, nullable=True)
    
    # Relations
    user = relationship("User", foreign_keys=[user_id], back_populates="souscriptions")
    produit_assurance = relationship("ProduitAssurance", back_populates="souscriptions")
    projet_voyage = relationship("ProjetVoyage", back_populates="souscriptions")
    courtier = relationship("Courtier")
    paiements = relationship("Paiement", back_populates="souscription", cascade="all, delete-orphan")
    questionnaires = relationship("Questionnaire", back_populates="souscription", cascade="all, delete-orphan")
    attestations = relationship("Attestation", back_populates="souscription", cascade="all, delete-orphan")
    ia_analyses = relationship("IAAnalysis", back_populates="souscription", cascade="all, delete-orphan")
