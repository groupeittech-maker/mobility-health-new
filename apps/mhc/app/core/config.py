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
    ASSURANCE_NAME: str = "Mobility Health Care"
    ASSURANCE_ADDRESS: str = "Plateau, Abidjan, Cote d'Ivoire"
    ASSURANCE_PHONE: str = "+225 00 00 00 00"
    ASSURANCE_EMAIL: str = "support@mobilityhealth.com"
    ASSURANCE_AGENT_NAME: str = "Equipe Mobility Health Care"
    ASSURANCE_AGENT_TITLE: str = "Représentant habilité"
    ASSURANCE_CITY: str = "Abidjan"
    ASSURANCE_SITE_WEB: str = "https://srv1324425.hstgr.cloud"
    ASSURANCE_ALERT_CENTER: str = "+242 05 098 35 35"

    # Annulation avant la date d'effet (ristourne) : la prime et les taxes sont
    # remboursées ; le coût de police et les frais de service MHC sont retenus
    # sauf si ces options sont activées.
    ANNULATION_REMBOURSE_COUT_POLICE: bool = False
    ANNULATION_REMBOURSE_FRAIS_SERVICES: bool = False

    # Sécurité des connexions (workflow V3 §3.2)
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    # Demande d'informations complémentaires (§4.2) : délai de réponse et rappel.
    INFO_REQUEST_DELAY_HOURS: int = 48
    INFO_REQUEST_REMINDER_HOURS: int = 24
    # Documents consultables après la fin du contrat (§5), puis masqués.
    DOCUMENTS_RETENTION_DAYS: int = 365
    
    # Email (SMTP) — mode "stub" court-circuite l'envoi (tests, dev sans SMTP)
    EMAIL_DELIVERY_MODE: str = "live"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_SECURITY: str = "starttls"  # starttls, ssl, plain
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@mobilityhealth.com"
    SMTP_FROM_NAME: str = "Mobility Health Care"
    
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
    # AfriPaie (orchestrateur de paiement)
    PAYMENT_SERVICE_URL: str = ""
    PAYMENT_SERVICE_API_KEY: str = ""  # sk_test_… ou sk_live_…
    PAYMENT_SERVICE_MODE: str = "stub"
    # Secret whsec_… du endpoint webhook déclaré via POST /v1/webhook-endpoints
    PAYMENT_SERVICE_WEBHOOK_SECRET: str = ""
    # URL publique du frontend (redirection après paiement hébergé AfriPaie)
    FRONTEND_BASE_URL: str = "http://localhost:8899"
    PAYMENT_CHECKOUT_SUCCESS_URL: str = ""  # défaut : {FRONTEND_BASE_URL}/payment-return.html?result=success
    PAYMENT_CHECKOUT_CANCEL_URL: str = ""   # défaut : {FRONTEND_BASE_URL}/payment-return.html?result=cancel

    OCR_SERVICE_URL: str = ""
    OCR_SERVICE_API_KEY: str = ""
    OCR_SERVICE_MODE: str = "stub"

    TRUST_SERVICE_URL: str = ""
    TRUST_SERVICE_API_KEY: str = ""
    TRUST_SERVICE_MODE: str = "stub"

    # Messagerie IT-Tech — SMS / WhatsApp (codes de vérification, notifications)
    MESSAGING_SERVICE_URL: str = ""
    MESSAGING_SERVICE_API_KEY: str = ""
    MESSAGING_SERVICE_MODE: str = "stub"  # stub | live (agrégateur IT-Tech) | meta (WhatsApp Cloud API)

    # WhatsApp Business — Meta Cloud API (MESSAGING_SERVICE_MODE=meta)
    WHATSAPP_ACCESS_TOKEN: str = ""          # Token permanent (utilisateur système Meta)
    WHATSAPP_PHONE_NUMBER_ID: str = ""       # ID du numéro WhatsApp Business
    WHATSAPP_API_VERSION: str = "v20.0"
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = ""  # Token de vérification du webhook Meta
    WHATSAPP_VERIFICATION_TEMPLATE: str = ""  # Template approuvé pour les codes de vérification (ex. mhc_code_verification)
    WHATSAPP_TEMPLATE_LANG: str = "fr"        # Code langue des templates (fr / en / fr_FR…)

    # eKYC (IT-TECH) — session + webhooks
    EKYC_SERVICE_URL: str = ""
    EKYC_SERVICE_CLIENT_ID: str = ""
    EKYC_SERVICE_CLIENT_SECRET: str = ""
    EKYC_SERVICE_MODE: str = "stub"
    EKYC_WEBHOOK_SECRET: str = ""
    
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

