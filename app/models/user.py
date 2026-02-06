from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, ForeignKey, Date, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import Role
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    date_naissance = Column(Date, nullable=True)
    telephone = Column(String(20), nullable=True)
    sexe = Column(String(10), nullable=True)  # 'M', 'F', 'Autre'
    pays_residence = Column(String, nullable=True)
    nationalite = Column(String, nullable=True)
    numero_passeport = Column(String(50), nullable=True)
    validite_passeport = Column(Date, nullable=True)
    nom_contact_urgence = Column(String(100), nullable=True)
    contact_urgence = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(SQLEnum(Role), default=Role.USER, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Validation de l'inscription par le médecin MH (workflow : inscription → médecin MH valide → abonné peut se connecter)
    email_verified = Column(Boolean, default=False, nullable=False)
    validation_inscription = Column(String(20), nullable=True, index=True)  # pending, approved, rejected
    validation_inscription_par = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    validation_inscription_date = Column(DateTime, nullable=True)
    validation_inscription_notes = Column(Text, nullable=True)
    # Informations médicales recueillies à l'inscription (pour validation par le médecin MH)
    maladies_chroniques = Column(Text, nullable=True)  # diabète, HTA, asthme, épilepsie, drépanocytose, cardiopathie, etc.
    traitements_en_cours = Column(Text, nullable=True)  # médicaments réguliers
    antecedents_recents = Column(Text, nullable=True)   # hospitalisation, chirurgie, suivi médical < 6 mois
    grossesse = Column(Boolean, nullable=True)         # si concernée (femme)

    # Relations
    role_obj = relationship("RoleModel", back_populates="users", foreign_keys=[role_id])
    hospital = relationship("Hospital", back_populates="receptionists", foreign_keys=[hospital_id])
    created_by = relationship("User", remote_side=[id], foreign_keys=[created_by_id], post_update=True)
    contacts_proches = relationship("ContactProche", back_populates="user", cascade="all, delete-orphan")
    projets_voyage = relationship("ProjetVoyage", back_populates="user", cascade="all, delete-orphan")
    souscriptions = relationship("Souscription", foreign_keys="Souscription.user_id", back_populates="user", cascade="all, delete-orphan")
    paiements = relationship("Paiement", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    prestations = relationship("Prestation", back_populates="user", cascade="all, delete-orphan")
    rapports = relationship("Rapport", foreign_keys="Rapport.user_id", back_populates="user", cascade="all, delete-orphan")
    rapports_signed = relationship("Rapport", foreign_keys="Rapport.signe_par", back_populates="signataire")
    invoices_validated_medical = relationship("Invoice", foreign_keys="Invoice.validation_medicale_par", back_populates="validateur_medical")
    invoices_validated_sinistre = relationship("Invoice", foreign_keys="Invoice.validation_sinistre_par", back_populates="validateur_sinistre")
    invoices_validated_compta = relationship("Invoice", foreign_keys="Invoice.validation_compta_par", back_populates="validateur_compta")
    medecin_referent_hospitals = relationship(
        "Hospital",
        back_populates="medecin_referent",
        foreign_keys="Hospital.medecin_referent_id"
    )
    hospital_stays_created = relationship(
        "HospitalStay",
        foreign_keys="HospitalStay.created_by_id",
        back_populates="created_by"
    )
    hospital_stays_assigned = relationship(
        "HospitalStay",
        foreign_keys="HospitalStay.assigned_doctor_id",
        back_populates="assigned_doctor"
    )
    hospital_stays_reported = relationship(
        "HospitalStay",
        foreign_keys="HospitalStay.report_submitted_by",
        back_populates="report_author"
    )
    assureurs_comptables = relationship(
        "Assureur",
        back_populates="agent_comptable",
        foreign_keys="Assureur.agent_comptable_id"
    )
    assureur_agents = relationship("AssureurAgent", back_populates="user", cascade="all, delete-orphan")

