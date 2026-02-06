from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.enums import StatutWorkflowSinistre
from app.core.database import Base
from app.models.base import TimestampMixin


class SinistreProcessStep(Base, TimestampMixin):
    """Représente une étape métier du processus sinistre"""

    __tablename__ = "sinistre_process_steps"

    id = Column(Integer, primary_key=True, index=True)
    sinistre_id = Column(Integer, ForeignKey("sinistres.id", ondelete="CASCADE"), nullable=False, index=True)
    step_key = Column(String(64), nullable=False, index=True)
    titre = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    ordre = Column(Integer, nullable=False)
    statut = Column(String(20), default=StatutWorkflowSinistre.PENDING.value, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    details = Column(JSON, nullable=True)

    sinistre = relationship("Sinistre", back_populates="workflow_steps")
    actor = relationship("User")

