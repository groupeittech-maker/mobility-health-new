from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Courtier(Base, TimestampMixin):
    """Courtier en assurance lié à un assureur unique."""

    __tablename__ = "courtiers"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False, unique=True)
    pays = Column(String(100), nullable=False)
    logo_url = Column(String(500), nullable=True)
    adresse = Column(String(255), nullable=True)
    telephone = Column(String(50), nullable=True)
    agent_comptable_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assureur_id = Column(
        Integer,
        ForeignKey("assureurs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    commission_pct = Column(Numeric(5, 2), nullable=False, default=0)

    assureur = relationship("Assureur")
    agent_comptable = relationship("User", foreign_keys=[agent_comptable_id])

