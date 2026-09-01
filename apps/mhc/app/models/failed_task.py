"""
Modèle pour tracker les tâches Celery échouées
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class FailedTask(Base, TimestampMixin):
    """Modèle pour enregistrer les tâches Celery échouées"""
    __tablename__ = "failed_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, nullable=False, index=True)
    task_name = Column(String(255), nullable=False, index=True)
    task_args = Column(JSON, nullable=True)
    task_kwargs = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=False)
    error_traceback = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    queue_name = Column(String(100), nullable=True, index=True)
    
    def __repr__(self):
        return f"<FailedTask {self.task_id}: {self.task_name}>"

