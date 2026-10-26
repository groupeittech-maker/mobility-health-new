from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Ristourne(Base, TimestampMixin):
    """Remboursement partiel ou total de prime (annulation, modification à la baisse).

    Calculé et enregistré « à rembourser » par MyMHC ; la finance MHC confirme
    le remboursement effectué, ce qui génère la quittance de ristourne (code 120).
    """

    __tablename__ = "ristournes"

    id = Column(Integer, primary_key=True, index=True)
    souscription_id = Column(
        Integer, ForeignKey("souscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    avenant_id = Column(Integer, ForeignKey("avenants.id", ondelete="SET NULL"), nullable=True, index=True)
    paiement_id = Column(Integer, ForeignKey("paiements.id", ondelete="SET NULL"), nullable=True, index=True)

    numero = Column(String(120), unique=True, nullable=True, index=True)  # attribué à la confirmation
    statut = Column(String(20), nullable=False, default="a_rembourser", index=True)  # a_rembourser | rembourse
    motif = Column(Text, nullable=True)

    montant_prime = Column(Numeric(12, 2), nullable=False, default=0)
    montant_frais_police = Column(Numeric(12, 2), nullable=False, default=0)
    montant_taxes = Column(Numeric(12, 2), nullable=False, default=0)
    montant_total = Column(Numeric(12, 2), nullable=False, default=0)
    devise = Column(String(10), nullable=False, default="XAF")

    moyen_remboursement = Column(String(30), nullable=True)  # carte | mobile_money | virement | autre
    reference_remboursement = Column(String(200), nullable=True)
    confirmed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)

    souscription = relationship("Souscription")
    avenant = relationship("Avenant")
    paiement = relationship("Paiement")
    confirmed_by = relationship("User", foreign_keys=[confirmed_by_id])
