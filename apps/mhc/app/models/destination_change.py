from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class DestinationChangeRequest(Base, TimestampMixin):
    """Demande de changement de destination en cours de voyage (kit MyMHC).

    Le souscripteur demande un changement de destination (zone couverte par la
    police uniquement), en joignant son billet et un motif. La demande est
    validée par l'Assureur / l'admin avant application : à l'approbation, la
    destination du projet de voyage est mise à jour.
    """

    __tablename__ = "destination_change_requests"

    id = Column(Integer, primary_key=True, index=True)
    souscription_id = Column(
        Integer, ForeignKey("souscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    projet_voyage_id = Column(
        Integer, ForeignKey("projets_voyage.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Destination actuelle (snapshot) et nouvelle destination demandée
    ancienne_destination = Column(String(200), nullable=True)
    destination_country_id = Column(
        Integer, ForeignKey("destination_countries.id", ondelete="SET NULL"), nullable=True
    )
    nouvelle_destination = Column(String(200), nullable=False)

    motif = Column(Text, nullable=True)
    billet_document_id = Column(
        Integer, ForeignKey("projet_voyage_documents.id", ondelete="SET NULL"), nullable=True
    )

    # en_attente | approuvee | refusee
    statut = Column(String(20), nullable=False, default="en_attente", index=True)
    decision_note = Column(Text, nullable=True)
    decided_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at = Column(DateTime, nullable=True)

    souscription = relationship("Souscription")
    projet_voyage = relationship("ProjetVoyage")
    user = relationship("User", foreign_keys=[user_id])
    destination_country = relationship("DestinationCountry")
    billet_document = relationship("ProjetVoyageDocument")
    decided_by = relationship("User", foreign_keys=[decided_by_id])
