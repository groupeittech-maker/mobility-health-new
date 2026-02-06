"""
═══════════════════════════════════════════════════════════════════════════════
CONFIGURATION DU MODULE IA - LOCAL ET PRODUCTION
═══════════════════════════════════════════════════════════════════════════════

Ce fichier gère la configuration pour :
- Environnement LOCAL (développement)
- Environnement PRODUCTION (VPS Hostinger)

UTILISATION:
    from ia_module.config import config
    
    # Récupérer le chemin Tesseract
    tesseract_path = config.TESSERACT_CMD
    
    # Vérifier l'environnement
    if config.IS_PRODUCTION:
        print("Mode production")

═══════════════════════════════════════════════════════════════════════════════
"""

import os
import platform
from pathlib import Path


class Config:
    """Configuration du module IA selon l'environnement"""
    
    def __init__(self):
        # Détecter l'environnement
        self.ENV = os.getenv("ENV", "development")  # 'development' ou 'production'
        self.IS_PRODUCTION = self.ENV == "production"
        self.IS_DEVELOPMENT = not self.IS_PRODUCTION
        
        # Détecter le système d'exploitation
        self.OS = platform.system()  # 'Windows', 'Linux', 'Darwin' (macOS)
        self.IS_WINDOWS = self.OS == "Windows"
        self.IS_LINUX = self.OS == "Linux"
        
        # ═══════════════════════════════════════════════════════════
        # CONFIGURATION TESSERACT OCR
        # ═══════════════════════════════════════════════════════════
        
        if self.IS_WINDOWS:
            # Windows (développement local)
            self.TESSERACT_CMD = os.getenv(
                "TESSERACT_CMD",
                r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )
            self.POPPLER_PATH = os.getenv(
                "POPPLER_PATH",
                r"C:\Program Files\poppler-25.07.0\Library\bin"
            )
        else:
            # Linux (VPS Hostinger / Production)
            self.TESSERACT_CMD = os.getenv(
                "TESSERACT_CMD",
                "/usr/bin/tesseract"
            )
            self.POPPLER_PATH = os.getenv(
                "POPPLER_PATH",
                "/usr/bin"
            )
        
        # ═══════════════════════════════════════════════════════════
        # CONFIGURATION API (si utilisé comme microservice)
        # ═══════════════════════════════════════════════════════════
        
        self.API_HOST = os.getenv("IA_API_HOST", "127.0.0.1")
        self.API_PORT = int(os.getenv("IA_API_PORT", "8001"))
        
        # URL du service IA (pour le backend principal)
        if self.IS_PRODUCTION:
            # En production, le service IA tourne sur le même serveur
            self.IA_SERVICE_URL = os.getenv(
                "IA_SERVICE_URL",
                f"http://localhost:{self.API_PORT}"
            )
        else:
            # En local
            self.IA_SERVICE_URL = os.getenv(
                "IA_SERVICE_URL",
                f"http://127.0.0.1:{self.API_PORT}"
            )
        
        # ═══════════════════════════════════════════════════════════
        # CONFIGURATION FICHIERS TEMPORAIRES
        # ═══════════════════════════════════════════════════════════
        
        if self.IS_WINDOWS:
            self.TEMP_DIR = os.getenv("TEMP_DIR", os.path.join(os.environ.get("TEMP", "/tmp"), "ia_module"))
        else:
            self.TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/ia_module")
        
        # Créer le dossier temp s'il n'existe pas
        Path(self.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        
        # ═══════════════════════════════════════════════════════════
        # CONFIGURATION LOGS
        # ═══════════════════════════════════════════════════════════
        
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if self.IS_PRODUCTION else "DEBUG")
        
        if self.IS_PRODUCTION:
            self.LOG_DIR = os.getenv("LOG_DIR", "/var/log/ia_module")
        else:
            self.LOG_DIR = os.getenv("LOG_DIR", "./logs")
        
        # ═══════════════════════════════════════════════════════════
        # CONFIGURATION SÉCURITÉ
        # ═══════════════════════════════════════════════════════════
        
        self.API_KEY = os.getenv("IA_API_KEY", "SECRET_IA_KEY_2025")
        
    def to_dict(self) -> dict:
        """Retourne la configuration sous forme de dictionnaire"""
        return {
            "env": self.ENV,
            "is_production": self.IS_PRODUCTION,
            "os": self.OS,
            "tesseract_cmd": self.TESSERACT_CMD,
            "poppler_path": self.POPPLER_PATH,
            "api_host": self.API_HOST,
            "api_port": self.API_PORT,
            "ia_service_url": self.IA_SERVICE_URL,
            "temp_dir": self.TEMP_DIR,
            "log_level": self.LOG_LEVEL
        }
    
    def print_config(self):
        """Affiche la configuration actuelle"""
        print("\n" + "="*60)
        print("   CONFIGURATION MODULE IA")
        print("="*60)
        print(f"   Environnement: {self.ENV}")
        print(f"   Système: {self.OS}")
        print(f"   Production: {self.IS_PRODUCTION}")
        print(f"   Tesseract: {self.TESSERACT_CMD}")
        print(f"   Poppler: {self.POPPLER_PATH}")
        print(f"   API URL: {self.IA_SERVICE_URL}")
        print(f"   Temp Dir: {self.TEMP_DIR}")
        print("="*60 + "\n")


# Instance globale de configuration
config = Config()


# ═══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════

def get_tesseract_cmd() -> str:
    """Retourne le chemin vers Tesseract selon l'environnement"""
    return config.TESSERACT_CMD


def get_poppler_path() -> str:
    """Retourne le chemin vers Poppler selon l'environnement"""
    return config.POPPLER_PATH


def is_production() -> bool:
    """Vérifie si on est en production"""
    return config.IS_PRODUCTION


def get_ia_service_url() -> str:
    """Retourne l'URL du service IA"""
    return config.IA_SERVICE_URL





