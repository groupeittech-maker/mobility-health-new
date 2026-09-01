from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class RoleModel(Base, TimestampMixin):
    """Modèle pour les rôles dans le système"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    permissions = Column(Text, nullable=True)  # JSON string pour les permissions
    
    # Relations
    users = relationship("User", back_populates="role_obj", foreign_keys="User.role_id")
