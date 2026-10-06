from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class CourtierAgent(Base, TimestampMixin):
    """Table de liaison pour gérer les agents (production, souscription, sinistre) d'un courtier.

    L'agent comptable reste porté par Courtier.agent_comptable_id.
    """

    __tablename__ = "courtier_agents"

    id = Column(Integer, primary_key=True, index=True)
    courtier_id = Column(Integer, ForeignKey("courtiers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type_agent = Column(String(50), nullable=False)  # 'production', 'souscription', 'sinistre'

    # Contrainte unique : un agent ne peut être affecté qu'à un seul courtier
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_courtier_agent_user'),
    )

    # Relations
    courtier = relationship("Courtier", back_populates="agents")
    user = relationship("User", back_populates="courtier_agents")
