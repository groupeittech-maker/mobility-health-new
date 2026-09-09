from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Avenant(Base, TimestampMixin):
    """Avenant au cycle de vie de la police d'assurance.

    Types : suspension, réémission, annulation (référentiel documentaire MHC,
    2ᵉ tableau). La suspension est demandée par le souscripteur depuis MyMHC
    puis validée par l'assureur (rôle agent_sinistre_assureur) ; la réémission
    lève la suspension ; l'annulation met fin à la police.
    """

    __tablename__ = "avenants"

    id = Column(Integer, primary_key=True, index=True)
    souscription_id = Column(
        Integer, ForeignKey("souscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type_avenant = Column(String(20), nullable=False, index=True)  # suspension | reemission | annulation
    numero = Column(String(120), unique=True, nullable=False, index=True)
    # demande (suspension en attente) | valide | refuse | emis (réémission/annulation)
    statut = Column(String(20), nullable=False, default="demande", index=True)

    # Demande de suspension : motifs cochés + précision + pièces justificatives (optionnel)
    motifs = Column(JSON, nullable=True)          # liste de clés cochées
    motif_autre = Column(Text, nullable=True)
    pieces_jointes = Column(JSON, nullable=True)  # liste {nom, bucket, path}

    # Décision de l'assureur (suspension)
    decision_assureur = Column(String(20), nullable=True)  # approved | rejected
    decided_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime, nullable=True)

    date_effet = Column(DateTime, nullable=True)
    date_echeance = Column(DateTime, nullable=True)

    # Chaînage : la réémission/annulation référence l'avenant de suspension parent
    parent_avenant_id = Column(
        Integer, ForeignKey("avenants.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # PDF généré
    pdf_bucket = Column(String(100), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    payload = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    souscription = relationship("Souscription")
    decided_by = relationship("User", foreign_keys=[decided_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    parent_avenant = relationship("Avenant", remote_side=[id], foreign_keys=[parent_avenant_id])

    @property
    def fichiers(self) -> list:
        """Pièces justificatives réellement téléversées (métadonnées, hors bytes)."""
        return list((self.payload or {}).get("fichiers") or [])
