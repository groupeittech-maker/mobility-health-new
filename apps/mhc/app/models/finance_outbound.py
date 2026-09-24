"""Paiements sortants MHC — cessions, rétentions, commissions, taxes, rétrocessions."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PaiementFournisseur(Base):
    """Flux de paiement sortant vers un bénéficiaire (assureur, réassureur,
    intermédiaire, fisc, hôpital, réassureur-quote-part…)."""

    __tablename__ = "paiements_fournisseurs"

    TYPES = {
        "cession_reassurance",
        "retention_assureur",
        "commission_cession",
        "commission_courtage",
        "cout_police",
        "taxe",
        "taxe_additionnelle",
        "retrocession_mhc",
        "quote_part_sinistre_reassureur",
        "facture_hopital",
    }

    STATUTS = {"a_payer", "controle", "paye", "annule"}

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(100), unique=True, nullable=False, index=True)
    type_paiement = Column(String(50), nullable=False, index=True)
    beneficiaire_type = Column(String(40), nullable=False)  # reassureur | assureur | courtier | fisc | hopital | mhc | interne
    beneficiaire_id = Column(Integer, nullable=True)  # id dans la table du bénéficiaire (reassureurs/assureurs/courtiers/hospitals)
    beneficiaire_nom = Column(String(200), nullable=True)
    montant = Column(Numeric(14, 2), nullable=False)
    devise = Column(String(10), nullable=False, default="XAF")
    periode = Column(String(20), nullable=True)  # ex: "2026-09"
    sinistre_id = Column(Integer, ForeignKey("sinistres.id", ondelete="SET NULL"), nullable=True, index=True)
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    produit_id = Column(Integer, ForeignKey("produits_assurance.id", ondelete="SET NULL"), nullable=True)
    statut = Column(String(20), nullable=False, default="a_payer", index=True)
    description = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    controlled_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    controlled_at = Column(DateTime, nullable=True)
    paid_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    sinistre = relationship("Sinistre", foreign_keys=[sinistre_id])
