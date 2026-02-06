from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)  # Timestamp de l'action audité
    method = Column(String, nullable=False)
    path = Column(String, nullable=False)
    query_params = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_role = Column(String, nullable=True)
    client_ip = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=False)
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Durée de la requête en millisecondes
    
    # Relations
    user = relationship("User", foreign_keys=[user_id])

