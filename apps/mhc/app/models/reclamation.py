"""Réclamations MyMHC (workflow V3 §8.1)."""
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Reclamation(Base, TimestampMixin):
    __tablename__ = "reclamations"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(40), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    categorie = Column(String(40), nullable=False, index=True)
    objet = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    personne_concernee = Column(String(200), nullable=True)
    pieces_jointes = Column(JSON, nullable=True)
    coordonnees = Column(JSON, nullable=True)
    # recue → en_analyse → infos_requises → traitee (réponse motivée) → cloturee
    statut = Column(String(30), nullable=False, default="recue", index=True)
    reponse = Column(Text, nullable=True)
    complexe = Column(Boolean, nullable=False, default=False, server_default="false")
    # Contestation : demande de réexamen liée à la réclamation initiale.
    parent_id = Column(Integer, ForeignKey("reclamations.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    echeance_premiere_reponse = Column(DateTime, nullable=True)
    echeance_resolution = Column(DateTime, nullable=True)
    premiere_reponse_at = Column(DateTime, nullable=True)
    traitee_at = Column(DateTime, nullable=True)
    cloturee_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    souscription = relationship("Souscription")
    parent = relationship("Reclamation", remote_side=[id])
    events = relationship(
        "ReclamationEvent",
        back_populates="reclamation",
        cascade="all, delete-orphan",
        order_by="ReclamationEvent.id",
    )


class ReclamationEvent(Base, TimestampMixin):
    """Historique d'une réclamation (création, changements de statut, messages)."""

    __tablename__ = "reclamation_events"

    id = Column(Integer, primary_key=True, index=True)
    reclamation_id = Column(Integer, ForeignKey("reclamations.id", ondelete="CASCADE"), nullable=False, index=True)
    auteur_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    type_event = Column(String(30), nullable=False)  # creation | statut | message | contestation
    statut = Column(String(30), nullable=True)
    message = Column(Text, nullable=True)
    visible_assure = Column(Boolean, nullable=False, default=True, server_default="true")

    reclamation = relationship("Reclamation", back_populates="events")
