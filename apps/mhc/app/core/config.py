from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field, computed_field
from typing import List
import json


def _default_cors_str() -> str:
    return ",".join([
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:8080", "http://127.0.0.1:8080",
        "http://localhost:8000", "http://127.0.0.1:8000",
        "https://srv1324425.hstgr.cloud", "https://api.srv1324425.hstgr.cloud",
        "https://mobility-health.ittechmed.com", "https://www.mobility-health.ittechmed.com",
    ])


class Settings(BaseSettings):
    # Database
    # Pour le développement : SQLite (par défaut)
    # Pour la production : PostgreSQL (décommenter et configurer DATABASE_URL)
    DATABASE_URL: str = "sqlite:///./mobility_health.db"  # SQLite pour développement
    # DATABASE_URL: str  # PostgreSQL pour production - décommenter quand nécessaire
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Minio
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False
    # Si MinIO n’est pas utilisable : répertoire persistant (volume Docker) pour les pièces projet
    # (ex. photo identité e-carte). Les fichiers sont sous project-documents/{projet_voyage_id}/...
    LOCAL_FILE_STORAGE_ROOT: str = ""
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Application
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    # CORS: lu depuis .env comme chaîne (évite le parsing JSON). Format: URLs séparées par des virgules ou JSON.
    cors_origins_raw: str = Field(default_factory=_default_cors_str, validation_alias="CORS_ORIGINS")

    @computed_field
    @property
    def CORS_ORIGINS(self) -> List[str]:
        s = (self.cors_origins_raw or "").strip()
        if not s:
            return [x.strip() for x in _default_cors_str().split(",") if x.strip()]
        try:
            out = json.loads(s)
            return list(out) if isinstance(out, list) else [str(out)]
        except json.JSONDecodeError:
            return [x.strip() for x in s.split(",") if x.strip()]
    
    # Assurance / informations de contact pour les attestations
    ASSURANCE_NAME: str = "Mobility Health"
    ASSURANCE_ADDRESS: str = "Plateau, Abidjan, Cote d'Ivoire"
    ASSURANCE_PHONE: str = "+225 00 00 00 00"
    ASSURANCE_EMAIL: str = "support@mobilityhealth.com"
    ASSURANCE_AGENT_NAME: str = "Equipe Mobility Health"
    ASSURANCE_AGENT_TITLE: str = "Représentant habilité"
    ASSURANCE_CITY: str = "Abidjan"
    ASSURANCE_SITE_WEB: str = "https://srv1324425.hstgr.cloud"
    
    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_SECURITY: str = "starttls"  # starttls, ssl, plain
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@mobilityhealth.com"
    SMTP_FROM_NAME: str = "Mobility Health"
    
    # SMS (Twilio ou autre)
    SMS_PROVIDER: str = "twilio"  # twilio, aws_sns, etc.
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    
    # Push Notifications (FCM)
    # HTTP v1 (recommandé) : JSON compte de service Firebase (fichier ou chaîne JSON)
    FCM_SERVICE_ACCOUNT_PATH: str = ""
    FCM_SERVICE_ACCOUNT_JSON: str = ""
    # Ancienne API (legacy) — souvent indisponible sur les nouveaux projets Google
    FCM_SERVER_KEY: str = ""
    FCM_PROJECT_ID: str = ""
    
    # Attestations / Vérification
    ATTESTATION_VERIFICATION_BASE_URL: str = "https://srv1324425.hstgr.cloud/api/v1"
    # URL publique de l'API (sans /api/v1) pour générer les URLs de proxy (e-carte, etc.)
    # Si défini et que MinIO est interne (minio:9000, localhost), les URLs présignées MinIO
    # sont remplacées par des URLs passant par l'API (pour que le navigateur puisse charger l'image).
    API_PUBLIC_BASE_URL: str = ""  # ex: https://srv1324425.hstgr.cloud
    
    # Celery
    CELERY_BROKER_URL: str = ""  # Si différent de REDIS_URL
    CELERY_RESULT_BACKEND: str = ""  # Si différent de REDIS_URL

    # Services externes IT-Tech (stub | live)
    PAYMENT_SERVICE_URL: str = ""
    PAYMENT_SERVICE_API_KEY: str = ""
    PAYMENT_SERVICE_MODE: str = "stub"

    OCR_SERVICE_URL: str = ""
    OCR_SERVICE_API_KEY: str = ""
    OCR_SERVICE_MODE: str = "stub"

    TRUST_SERVICE_URL: str = ""
    TRUST_SERVICE_API_KEY: str = ""
    TRUST_SERVICE_MODE: str = "stub"
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields from .env
    )


settings = Settings()

# Validation des variables critiques en production
if settings.ENVIRONMENT.lower() == "production":
    if not settings.SECRET_KEY or settings.SECRET_KEY == "your-secret-key-change-in-production":
        raise ValueError("SECRET_KEY doit être défini et sécurisé en production!")
    if settings.DATABASE_URL.startswith("sqlite"):
        raise ValueError("SQLite ne doit pas être utilisé en production! Utilisez PostgreSQL.")
    if not settings.MINIO_ENDPOINT or not settings.MINIO_ACCESS_KEY or not settings.MINIO_SECRET_KEY:
        raise ValueError("Les paramètres MinIO doivent être configurés en production!")

