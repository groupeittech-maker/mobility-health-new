from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Notification(Base, TimestampMixin):
    """Modèle pour les notifications utilisateur"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type_notification = Column(String(50), nullable=False)  # questionnaire_reminder, etc.
    titre = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    lien_relation_id = Column(Integer, nullable=True)  # ID lié (questionnaire_id, souscription_id, etc.)
    lien_relation_type = Column(String(50), nullable=True)  # Type de relation (questionnaire, souscription, etc.)
    
    # Relations
    user = relationship("User", back_populates="notifications")

