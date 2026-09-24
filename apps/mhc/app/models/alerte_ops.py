"""Extensions opérationnelles des alertes SOS — centre d'alertes urgence.

- AlerteNote : notes horodatées des opérateurs / médecin-conseil.
- AlerteEvent : timeline de l'alerte (réception, évaluation, orientation…).
- AlerteStatutMedical : état médical de l'assuré saisi lors de l'appel.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AlerteNote(Base):
    __tablename__ = "alerte_notes"

    id = Column(Integer, primary_key=True, index=True)
    alerte_id = Column(Integer, ForeignKey("alertes.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_name = Column(String(200), nullable=True)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    alerte = relationship("Alerte", foreign_keys=[alerte_id])


class AlerteEvent(Base):
    """Événement de la timeline « Historique de l'alerte »."""

    __tablename__ = "alerte_events"

    id = Column(Integer, primary_key=True, index=True)
    alerte_id = Column(Integer, ForeignKey("alertes.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # reception, evaluation, orientation, note, transfert, statut, action…
    label = Column(String(300), nullable=False)
    details = Column(JSON, nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_name = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    alerte = relationship("Alerte", foreign_keys=[alerte_id])


class AlerteStatutMedical(Base):
    """Statut médical de l'assuré renseigné « selon l'appel » (maquette)."""

    __tablename__ = "alerte_statuts_medicaux"

    id = Column(Integer, primary_key=True, index=True)
    alerte_id = Column(Integer, ForeignKey("alertes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    etat_patient = Column(String(50), nullable=True)  # conscient, inconscient, agite…
    motifs_symptomes = Column(Text, nullable=True)
    besoins_immediats = Column(Text, nullable=True)
    allergies_connues = Column(Text, nullable=True)
    traitements_en_cours = Column(Text, nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_name = Column(String(200), nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    alerte = relationship("Alerte", foreign_keys=[alerte_id])
