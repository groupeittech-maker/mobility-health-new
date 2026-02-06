from datetime import datetime
from sqlalchemy import Column, DateTime
from app.core.database import Base


class TimestampMixin:
    """Mixin for adding timestamp fields"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

