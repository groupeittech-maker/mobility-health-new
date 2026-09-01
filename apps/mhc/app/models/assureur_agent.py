from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class AssureurAgent(Base, TimestampMixin):
    """Table de liaison pour gérer les agents (comptable, production, sinistre) d'un assureur"""
    
    __tablename__ = "assureur_agents"
    
    id = Column(Integer, primary_key=True, index=True)
    assureur_id = Column(Integer, ForeignKey("assureurs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type_agent = Column(String(50), nullable=False)  # 'comptable', 'production', 'sinistre'
    
    # Contrainte unique : un agent ne peut être affecté qu'à un seul assureur
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_assureur_agent_user'),
    )
    
    # Relations
    assureur = relationship("Assureur", back_populates="agents")
    user = relationship("User", back_populates="assureur_agents")

