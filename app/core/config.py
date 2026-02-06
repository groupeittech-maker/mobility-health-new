from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List


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
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Application
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    # CORS: Liste des origines autorisées pour les requêtes cross-origin
    # Pour le développement mobile, ajoutez l'IP de votre réseau local
    # Format: http://IP:PORT ou http://IP:PORT/api/v1
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        # Pour l'émulateur Android
        "http://10.0.2.2:8000",
        # Pour les appareils mobiles sur le réseau local
        "http://192.168.1.82:8000",
        "http://192.168.1.117:8000",
        # Production : serveur Hostinger
        "https://srv1324425.hstgr.cloud",
        # Autres domaines éventuels (ex. alias)
        "https://mobility-health.ittechmed.com",
        "https://www.mobility-health.ittechmed.com",
        # Ajoutez d'autres IPs/domaines si nécessaire (ou via CORS_ORIGINS dans .env)
    ]
    
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
    FCM_SERVER_KEY: str = ""
    FCM_PROJECT_ID: str = ""
    
    # Attestations / Vérification
<<<<<<< HEAD
    ATTESTATION_VERIFICATION_BASE_URL: str = "https://srv1324425.hstgr.cloud/api/v1"
=======
    ATTESTATION_VERIFICATION_BASE_URL: str = "https://mobility-health.ittechmed.com/api/v1"
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
    
    # Celery
    CELERY_BROKER_URL: str = ""  # Si différent de REDIS_URL
    CELERY_RESULT_BACKEND: str = ""  # Si différent de REDIS_URL
    
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

