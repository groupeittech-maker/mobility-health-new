from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class HospitalExamTarif(Base, TimestampMixin):
    """Tarification personnalisée des examens pour un hôpital."""

    __tablename__ = "hospital_exam_tarifs"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(
        Integer,
        ForeignKey("hospitals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nom = Column(String(200), nullable=False)
    montant = Column(Numeric(10, 2), nullable=False)

    hospital = relationship("Hospital", back_populates="exam_tarifs")

















