from sqlalchemy import Column, Integer, String, Numeric, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from app.core.enums import Role


class Hospital(Base, TimestampMixin):
    """Modèle pour les hôpitaux"""
    __tablename__ = "hospitals"
    
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False, index=True)
    adresse = Column(String(500), nullable=True)
    ville = Column(String(100), nullable=True)
    pays = Column(String(100), nullable=True)
    code_postal = Column(String(20), nullable=True)
    telephone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=False)  # Coordonnées GPS
    longitude = Column(Numeric(11, 8), nullable=False)
    est_actif = Column(Boolean, default=True, nullable=False)
    specialites = Column(Text, nullable=True)  # JSON ou texte séparé par virgules
    capacite_lits = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    medecin_referent_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Relations
    sinistres = relationship("Sinistre", back_populates="hospital", foreign_keys="Sinistre.hospital_id")
    prestations = relationship("Prestation", back_populates="hospital", cascade="all, delete-orphan")
    rapports = relationship("Rapport", back_populates="hospital", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="hospital", cascade="all, delete-orphan")
    receptionists = relationship(
        "User",
        back_populates="hospital",
        cascade="all",
        passive_deletes=True,
        foreign_keys="User.hospital_id"
    )
    medecin_referent = relationship(
        "User",
        foreign_keys=[medecin_referent_id],
        back_populates="medecin_referent_hospitals",
    )
    hospital_stays = relationship(
        "HospitalStay",
        back_populates="hospital",
        cascade="all, delete-orphan"
    )
    exam_tarifs = relationship(
        "HospitalExamTarif",
        back_populates="hospital",
        cascade="all, delete-orphan"
    )
    act_tarifs = relationship(
        "HospitalActTarif",
        back_populates="hospital",
        cascade="all, delete-orphan"
    )

    @property
    def receptionists_count(self) -> int:
        if not self.receptionists:
            return 0
        return len([user for user in self.receptionists if user.role == Role.AGENT_RECEPTION_HOPITAL])

    @property
    def doctors_count(self) -> int:
        from app.core.enums import Role as _Role
        if not self.receptionists:
            return 0
        # Uniquement les médecins hospitaliers (pas les médecins génériques)
        return len([user for user in self.receptionists if user.role == _Role.MEDECIN_HOPITAL])

    @property
    def accountants_count(self) -> int:
        if not self.receptionists:
            return 0
        return len([user for user in self.receptionists if user.role == Role.AGENT_COMPTABLE_HOPITAL])