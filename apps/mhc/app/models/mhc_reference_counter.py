from sqlalchemy import Column, Integer, String, UniqueConstraint
from app.core.database import Base
from app.models.base import TimestampMixin


class MhcReferenceCounter(Base, TimestampMixin):
    """Compteur annuel pour les numéros d'ordre MHC (police, sinistre, bons)."""

    __tablename__ = "mhc_reference_counters"
    __table_args__ = (
        UniqueConstraint("counter_key", "year", name="uq_mhc_reference_counters_key_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    counter_key = Column(String(40), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    last_value = Column(Integer, nullable=False, default=0)
