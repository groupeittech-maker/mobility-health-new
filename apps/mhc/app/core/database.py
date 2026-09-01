import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


def _get_database_url() -> str:
    # Variables d'environnement Docker (compose) prioritaires sur le .env embarqué dans l'image.
    return os.environ.get("DATABASE_URL") or getattr(settings, "DATABASE_URL", None) or "sqlite:///./mobility_health.db"


engine = create_engine(
    _get_database_url(),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


















