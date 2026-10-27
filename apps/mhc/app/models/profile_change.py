"""Profil assuré : demandes de modification soumises à validation MHC et enfants bénéficiaires."""
from sqlalchemy import JSON, Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import deferred, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class ProfileChangeRequest(Base, TimestampMixin):
    """Modification d'identité (nom, naissance, nationalité, résidence, pièce) validée par MHC (§3.3).

    Tant que la demande est en attente, le compte reste utilisable avec les anciennes
    données ; en cas de refus, les anciennes données sont conservées et le motif communiqué.
    """

    __tablename__ = "profile_change_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    champs = Column(JSON, nullable=False)
    anciennes_valeurs = Column(JSON, nullable=True)
    piece_identite = deferred(Column(JSON, nullable=True))
    statut = Column(String(20), nullable=False, default="pending", index=True)  # pending | approved | rejected
    motif_refus = Column(Text, nullable=True)
    decided_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class EnfantBeneficiaire(Base, TimestampMixin):
    """Enfant bénéficiaire géré par le parent (pas de compte autonome, §1 et §4.3).

    Retirer un enfant d'un brouillon ne supprime pas son profil : il peut être réajouté.
    """

    __tablename__ = "enfants_beneficiaires"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    nom = Column(String(120), nullable=False)
    prenom = Column(String(120), nullable=True)
    date_naissance = Column(Date, nullable=False)
    nationalite = Column(String(100), nullable=True)
    numero_piece = Column(String(60), nullable=True)
    validite_piece = Column(Date, nullable=True)
    lien_parente = Column(String(50), nullable=True)
    photo = deferred(Column(Text, nullable=True))
    copie_piece = deferred(Column(Text, nullable=True))
    actif = Column(Boolean, nullable=False, default=True, server_default="true")

    parent = relationship("User", foreign_keys=[parent_id])
