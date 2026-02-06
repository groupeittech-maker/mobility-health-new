from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import StatutProjetVoyage, QuestionnaireType
from app.models.base import TimestampMixin


class ProjetVoyage(Base, TimestampMixin):
    """Modèle pour les projets de voyage"""
    __tablename__ = "projets_voyage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    titre = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    destination = Column(String(200), nullable=False)
    destination_country_id = Column(
        Integer,
        ForeignKey("destination_countries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    date_depart = Column(DateTime, nullable=False)
    date_retour = Column(DateTime, nullable=True)
    nombre_participants = Column(Integer, default=1, nullable=False)
    statut = Column(SQLEnum(StatutProjetVoyage), default=StatutProjetVoyage.EN_PLANIFICATION, nullable=False)
    notes = Column(Text, nullable=True)
    budget_estime = Column(Numeric(10, 2), nullable=True)
    questionnaire_type = Column(
        SQLEnum(QuestionnaireType),
        default=QuestionnaireType.LONG,
        nullable=False,
    )
    
    # Relations
    user = relationship("User", back_populates="projets_voyage")
    souscriptions = relationship("Souscription", back_populates="projet_voyage")
    destination_country = relationship("DestinationCountry", backref="projets_voyage")
    documents = relationship(
        "ProjetVoyageDocument",
        back_populates="projet_voyage",
        cascade="all, delete-orphan",
    )
