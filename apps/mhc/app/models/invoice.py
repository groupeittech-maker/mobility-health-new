from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class InvoiceStatus(str):
    """Statut d'une facture"""
    DRAFT = "draft"
    PENDING_MEDICAL = "pending_medical"
    PENDING_SINISTRE = "pending_sinistre"
    PENDING_COMPTA = "pending_compta"
    VALIDATED = "validated"
    REJECTED = "rejected"
    PAID = "paid"


class Invoice(Base, TimestampMixin):
    """Modèle pour les factures basées sur les prestations"""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="RESTRICT"), nullable=False, index=True)
    hospital_stay_id = Column(Integer, ForeignKey("hospital_stays.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    numero_facture = Column(String(100), unique=True, nullable=False, index=True)
    
    # Montants
    montant_ht = Column(Numeric(12, 2), nullable=False)
    montant_tva = Column(Numeric(12, 2), default=0, nullable=False)
    montant_ttc = Column(Numeric(12, 2), nullable=False)
    
    # Dates
    date_facture = Column(DateTime, nullable=False)
    date_echeance = Column(DateTime, nullable=True)
    
    # Statut
    statut = Column(String(30), default=InvoiceStatus.DRAFT, nullable=False, index=True)
    
    # Validations
    validation_medicale = Column(String(20), nullable=True, index=True)  # pending, approved, rejected
    validation_medicale_par = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validation_medicale_date = Column(DateTime, nullable=True)
    validation_medicale_notes = Column(Text, nullable=True)
    
    validation_sinistre = Column(String(20), nullable=True, index=True)  # pending, approved, rejected
    validation_sinistre_par = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validation_sinistre_date = Column(DateTime, nullable=True)
    validation_sinistre_notes = Column(Text, nullable=True)
    
    validation_compta = Column(String(20), nullable=True, index=True)  # pending, approved, rejected
    validation_compta_par = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validation_compta_date = Column(DateTime, nullable=True)
    validation_compta_notes = Column(Text, nullable=True)
    
    notes = Column(Text, nullable=True)
    
    # Relations
    hospital = relationship("Hospital", back_populates="invoices")
    hospital_stay = relationship("HospitalStay", back_populates="invoice")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    validateur_medical = relationship("User", foreign_keys=[validation_medicale_par], back_populates="invoices_validated_medical")
    validateur_sinistre = relationship("User", foreign_keys=[validation_sinistre_par], back_populates="invoices_validated_sinistre")
    validateur_compta = relationship("User", foreign_keys=[validation_compta_par], back_populates="invoices_validated_compta")
    history_entries = relationship(
        "InvoiceHistory",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceHistory.created_at",
    )


class InvoiceItem(Base, TimestampMixin):
    """Modèle pour les lignes de facture (basées sur les prestations)"""
    __tablename__ = "invoice_items"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    prestation_id = Column(Integer, ForeignKey("prestations.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Informations de la ligne
    libelle = Column(String(200), nullable=False)
    quantite = Column(Integer, default=1, nullable=False)
    prix_unitaire = Column(Numeric(10, 2), nullable=False)
    montant_ht = Column(Numeric(10, 2), nullable=False)
    taux_tva = Column(Numeric(5, 2), default=0, nullable=False)
    montant_ttc = Column(Numeric(10, 2), nullable=False)
    
    # Relations
    invoice = relationship("Invoice", back_populates="items")
    prestation = relationship("Prestation", back_populates="invoice_items")


class InvoiceHistory(Base, TimestampMixin):
    __tablename__ = "invoice_history"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=True)
    previous_stage = Column(String(30), nullable=True)
    new_stage = Column(String(30), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    invoice = relationship("Invoice", back_populates="history_entries")
    actor = relationship("User")



