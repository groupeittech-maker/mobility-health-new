from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class ContactProche(Base, TimestampMixin):
    """Modèle pour les contacts proches d'un utilisateur"""
    __tablename__ = "contacts_proches"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    nom = Column(String(200), nullable=False)
    prenom = Column(String(200), nullable=False)
    telephone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    relation = Column(String(100), nullable=True)  # famille, ami, collegue, etc.
    est_contact_urgence = Column(Boolean, default=False, nullable=False)
    adresse = Column(String(500), nullable=True)
    pays = Column(String(100), nullable=True)
    
    # Relations
    user = relationship("User", back_populates="contacts_proches")
