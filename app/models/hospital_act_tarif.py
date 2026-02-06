from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class HospitalActTarif(Base, TimestampMixin):
    """Tarification personnalisée des actes médicaux pour un hôpital."""

    __tablename__ = "hospital_act_tarifs"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(
        Integer,
        ForeignKey("hospitals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(50), nullable=True, index=True)
    nom = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    montant = Column(Numeric(10, 2), nullable=False)

    hospital = relationship("Hospital", back_populates="act_tarifs")


