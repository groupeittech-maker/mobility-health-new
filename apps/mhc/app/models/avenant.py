from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Avenant(Base, TimestampMixin):
    """Avenant au cycle de vie de la police d'assurance (workflow MyMHC V3).

    Types : annulation (102), modification (107), prorogation (108).
    La suspension et la réémission n'existent pas dans MyMHC. Une seule
    demande peut être en cours par attestation (police).
    """

    __tablename__ = "avenants"

    id = Column(Integer, primary_key=True, index=True)
    souscription_id = Column(
        Integer, ForeignKey("souscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type_avenant = Column(String(20), nullable=False, index=True)  # annulation | modification | prorogation
    numero = Column(String(120), unique=True, nullable=False, index=True)
    # attente_paiement | attente_remboursement (en cours) | emis | abandonne | refuse
    statut = Column(String(30), nullable=False, default="emis", index=True)

    # Colonnes historiques (anciennes demandes de suspension) — conservées pour l'existant
    motifs = Column(JSON, nullable=True)
    motif_autre = Column(Text, nullable=True)  # Motif saisi par l'assuré
    pieces_jointes = Column(JSON, nullable=True)
    decision_assureur = Column(String(20), nullable=True)
    decided_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime, nullable=True)

    date_effet = Column(DateTime, nullable=True)
    date_echeance = Column(DateTime, nullable=True)

    # Dates de couverture avant / après l'avenant (modification, prorogation)
    date_debut_initiale = Column(DateTime, nullable=True)
    date_fin_initiale = Column(DateTime, nullable=True)
    nouvelle_date_debut = Column(DateTime, nullable=True)
    nouvelle_date_fin = Column(DateTime, nullable=True)

    # Ajustement de prime : complément à régler ou remboursement (ristourne)
    montant_ajustement = Column(Numeric(12, 2), nullable=True)
    nature_ajustement = Column(String(20), nullable=True)  # complement | remboursement | aucun
    paiement_id = Column(Integer, ForeignKey("paiements.id", ondelete="SET NULL"), nullable=True, index=True)

    parent_avenant_id = Column(
        Integer, ForeignKey("avenants.id", ondelete="SET NULL"), nullable=True, index=True
    )

    pdf_bucket = Column(String(100), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    payload = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    souscription = relationship("Souscription")
    paiement = relationship("Paiement", foreign_keys=[paiement_id])
    decided_by = relationship("User", foreign_keys=[decided_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    parent_avenant = relationship("Avenant", remote_side=[id], foreign_keys=[parent_avenant_id])
