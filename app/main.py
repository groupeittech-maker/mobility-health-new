from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi import status
from pathlib import Path
import logging
import traceback
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.database import engine, Base
from app.middleware.logging import LoggingMiddleware
from app.middleware.audit import AuditMiddleware
from app.api.v1 import api_router
from app.api.websocket import router as websocket_router

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création automatique des tables (COMMENTÉ - utiliser Alembic migrations à la place)
# Note: Il est recommandé d'utiliser Alembic migrations: alembic upgrade head
# Ce code est commenté mais conservé pour référence future si nécessaire

# Utiliser Alembic pour créer les tables:
# alembic upgrade head
logger.info("Utilisez 'alembic upgrade head' pour créer/mettre à jour les tables de la base de données")

app = FastAPI(
    title="Mobility Health API",
    description="API for Mobility Health Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    # Configuration pour détecter HTTPS derrière un proxy
    root_path="",
    # Désactiver les redirections automatiques de slash pour éviter les erreurs 307
    # Les routes alternatives sont définies dans chaque router pour accepter les deux formats
    redirect_slashes=False,
)


@app.on_event("startup")
async def startup_event():
    """Check database connection on startup"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_type = "SQLite" if settings.DATABASE_URL.startswith("sqlite") else "PostgreSQL"
        logger.info(f"Database connection successful ({db_type})")
    except OperationalError as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "n'existe pas" in error_msg:
            logger.error("=" * 60)
            logger.error("ERREUR: La base de données n'existe pas!")
            logger.error("=" * 60)
            if settings.DATABASE_URL.startswith("sqlite"):
                logger.error("Pour SQLite, le fichier sera créé automatiquement lors de la première migration.")
            else:
                logger.error("Pour PostgreSQL, exécutez:")
                logger.error("  psql -U postgres -c 'CREATE DATABASE mobility_health;'")
                logger.error("Ou utilisez Docker Compose:")
                logger.error("  docker-compose up -d db")
            logger.error("Puis exécutez les migrations:")
            logger.error("  alembic upgrade head")
            logger.error("=" * 60)
        else:
            logger.error(f"Erreur de connexion à la base de données: {e}")
            if not settings.DATABASE_URL.startswith("sqlite"):
                logger.error("Vérifiez que PostgreSQL est démarré et que les paramètres dans .env sont corrects")
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la vérification de la base de données: {e}")

# CORS middleware
# Filtrer "*" de la liste car il n'est pas compatible avec allow_credentials=True
cors_origins = [origin for origin in settings.CORS_ORIGINS if origin != "*"]

# En développement, autoriser toutes les origines localhost (pour Flutter Web)
if settings.DEBUG or settings.ENVIRONMENT.lower() in {"development", "local", "test"}:
    # Ajouter les origines localhost courantes
    localhost_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    # Ajouter un large éventail de ports pour Flutter Web (qui utilise des ports aléatoires)
    # Ports courants pour le développement web
    common_ports = list(range(3000, 9010))  # De 3000 à 9009
    for port in common_ports:
        localhost_origins.append(f"http://localhost:{port}")
        localhost_origins.append(f"http://127.0.0.1:{port}")
    
    # Fusionner avec les origines existantes
    cors_origins = list(set(cors_origins + localhost_origins))

# Si la liste est vide après filtrage, utiliser les origines par défaut
if not cors_origins:
    cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

logger.info(f"CORS configured for {len(cors_origins)} origins (DEBUG={settings.DEBUG}, ENV={settings.ENVIRONMENT})")
if settings.DEBUG or settings.ENVIRONMENT.lower() in {"development", "local", "test"}:
    logger.info("CORS: All localhost origins (ports 3000-9009) are allowed for development")
    # Afficher les 10 premières origines pour debug
    logger.debug(f"Sample CORS origins: {cors_origins[:10]}")

# Fonction helper pour vérifier si une origine est localhost
def is_localhost_origin(origin: str) -> bool:
    """Vérifie si l'origine est localhost"""
    if not origin:
        return False
    origin_lower = origin.lower()
    return (
        origin_lower.startswith("http://localhost:") or
        origin_lower.startswith("http://127.0.0.1:") or
        origin_lower.startswith("http://[::1]:")
    )

# Configuration CORS OBLIGATOIRE pour que les requêtes depuis le frontend fonctionnent
# IMPORTANT: allow_origins=["*"] + allow_credentials=True ne fonctionne PAS
# Il faut lister explicitement les origines autorisées

# En développement, utiliser une regex pour autoriser toutes les origines localhost
is_dev = settings.DEBUG or settings.ENVIRONMENT.lower() in {"development", "local", "test"}

if is_dev:
    # En développement : utiliser une regex pour autoriser toutes les origines localhost
    # Cela permet à Flutter Web d'utiliser n'importe quel port
    # Combiner la regex avec les origines explicites (IP réseau, etc.)
    cors_regex = r"http://localhost:\d+|http://127\.0\.0\.1:\d+|http://\[::1\]:\d+"
    # Ajouter les origines non-localhost à la liste
    non_localhost_origins = [origin for origin in cors_origins if not is_localhost_origin(origin)]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=cors_regex,
        allow_origins=non_localhost_origins,  # Origines non-localhost (IP réseau, etc.)
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    logger.info("CORS: Using regex pattern for localhost origins in development")
else:
    # En production : utiliser uniquement la liste explicite
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

# === GESTIONNAIRE D'ERREURS GLOBAL AVEC CORS ===
# Ceci permet d'inclure les headers CORS même en cas d'erreur 500
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestionnaire global pour capturer toutes les exceptions et ajouter les headers CORS"""
    # Log l'erreur
    logger.error(f"Erreur non gérée: {exc}")
    logger.error(traceback.format_exc())
    
    # Déterminer l'origine
    origin = request.headers.get("origin", "")
    
    # Préparer les headers CORS
    cors_headers = {}
    if origin:
        # En développement, autoriser toutes les origines localhost
        is_dev = settings.DEBUG or settings.ENVIRONMENT.lower() in {"development", "local", "test"}
        if is_dev and is_localhost_origin(origin):
            cors_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "*",
            }
        elif origin in cors_origins:
            cors_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "*",
            }
    
    # Retourner la réponse d'erreur avec les headers CORS
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "error_type": type(exc).__name__,
            "message": "Internal Server Error - voir les logs du serveur pour plus de détails"
        },
        headers=cors_headers
    )

# Middleware pour forcer HTTPS dans les redirections
class ForceHTTPSMiddleware(BaseHTTPMiddleware):
    """Middleware pour forcer HTTPS dans les URLs générées"""
    async def dispatch(self, request: Request, call_next):
        # Vérifier si on est derrière un proxy HTTPS
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
        is_https = forwarded_proto == "https"
        
        # Modifier le scope pour forcer HTTPS si détecté
        if is_https:
            request.scope["scheme"] = "https"
        
        response = await call_next(request)
        
        # Si c'est une redirection, forcer HTTPS
        if isinstance(response, RedirectResponse) and response.status_code in [301, 302, 307, 308]:
            location = response.headers.get("location", "")
            if location.startswith("http://"):
                # Remplacer http:// par https:// dans la redirection
                response.headers["location"] = location.replace("http://", "https://")
        
        return response

# Custom middlewares
app.add_middleware(ForceHTTPSMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuditMiddleware)

# Exception handlers globaux pour capturer toutes les erreurs
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'exceptions global pour logger toutes les erreurs"""
    logger.error(f"Exception non gérée: {type(exc).__name__}: {str(exc)}")
    logger.error(f"Traceback complet:\n{traceback.format_exc()}")
    logger.error(f"Request: {request.method} {request.url.path}")
    
    # Retourner une réponse JSON avec les détails de l'erreur
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"Erreur interne du serveur: {str(exc)}",
            "type": type(exc).__name__,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Gestionnaire pour les exceptions HTTP"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Gestionnaire pour les erreurs de validation"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )

# Include routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(websocket_router)

# Serve checkout page
@app.get("/checkout.html")
async def checkout_page():
    """Servir la page de checkout"""
    checkout_path = Path("frontend/checkout.html")
    if checkout_path.exists():
        return FileResponse(checkout_path)
    return {"error": "Checkout page not found"}


@app.get("/")
async def root():
    return {"message": "Mobility Health API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint avec vérification de l'heure du serveur"""
    from datetime import datetime
    import time
    
    server_time_utc = datetime.utcnow()
    server_timestamp = time.time()
    
    # Vérifier si l'heure semble correcte (dans les 5 dernières années et pas dans le futur)
    current_year = server_time_utc.year
    is_time_valid = 2020 <= current_year <= 2030
    
    return {
        "status": "healthy",
        "server_time_utc": server_time_utc.isoformat(),
        "server_timestamp": server_timestamp,
        "time_valid": is_time_valid,
        "warning": "Vérifiez la synchronisation NTP si time_valid est False" if not is_time_valid else None
    }

