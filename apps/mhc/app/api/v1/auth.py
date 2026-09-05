from datetime import timedelta
import random
import string
import logging
from urllib.parse import quote_plus
from types import SimpleNamespace
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    decode_inscription_activation_token,
    decode_email_verification_token,
)
from app.core.config import settings
from app.core.redis_client import get_redis
from app.core.enums import Role
from app.models.user import User
from app.models.hospital import Hospital
from app.services.user_service import UserService
from pydantic import BaseModel, EmailStr, field_validator, model_validator

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
logger = logging.getLogger(__name__)


def _issue_email_verification_code(user: User) -> None:
    """Génère un code à 6 chiffres, le stocke dans Redis (15 min) et envoie l'e-mail."""
    verification_code = "".join(random.choices(string.digits, k=6))
    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis.setex(
                    f"email_verification:{user.id}:{verification_code}",
                    900,
                    user.email,
                )
                redis.setex(
                    f"email_verification_email:{user.email}",
                    900,
                    verification_code,
                )
            except Exception as e:
                logger.error("Erreur stockage code vérification Redis: %s", e)
        else:
            logger.warning("Redis indisponible — code de vérification e-mail non persisté")
    except Exception as e:
        logger.warning("Redis indisponible (init): %s", e)
    try:
        UserService.send_verification_email(user, verification_code)
    except Exception as e:
        logger.error("Erreur envoi e-mail de vérification: %s", e)


def _sql_bool(val) -> bool:
    """Interprète une valeur booléenne issue du SQL (PostgreSQL / SQLite)."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    s = str(val).lower().strip()
    if s in ("true", "t", "1", "yes"):
        return True
    if s in ("false", "f", "0", "no", ""):
        return False
    return bool(val)


def _role_to_string(role_attr):
    """Extrait une chaîne de rôle depuis user.role (enum ou chaîne en base)."""
    if role_attr is None:
        return "user"
    if hasattr(role_attr, "value"):
        return getattr(role_attr, "value", "user")
    if isinstance(role_attr, str):
        return role_attr.lower() if role_attr else "user"
    return str(role_attr).lower() if str(role_attr) else "user"


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    username: str | None = None
    password: str
    full_name: str | None = None
    date_naissance: str | None = None  # Format ISO: YYYY-MM-DD
    telephone: str | None = None
    sexe: str | None = None  # 'M', 'F', 'Autre'
    pays_residence: str | None = None
    nationalite: str | None = None
    numero_passeport: str | None = None
    validite_passeport: str | None = None  # Format ISO: YYYY-MM-DD
    nom_contact_urgence: str | None = None
    contact_urgence: str | None = None
    maladies_chroniques: str | None = None
    traitements_en_cours: str | None = None
    antecedents_recents: str | None = None
    grossesse: bool | None = None

    @model_validator(mode="after")
    def set_username_from_email(self):
        """Auto-inscription : le nom d'utilisateur est l'adresse e-mail."""
        self.username = str(self.email).strip()
        return self

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str | None) -> str:
        """Valider le nom d'utilisateur (e-mail ou identifiant classique)."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Le nom d'utilisateur ne peut pas être vide")
        v = v.strip()
        if "@" in v:
            if len(v) > 255:
                raise ValueError("L'adresse e-mail est trop longue")
            return v
        if len(v) < 3:
            raise ValueError("Le nom d'utilisateur doit contenir au moins 3 caractères")
        if len(v) > 50:
            raise ValueError("Le nom d'utilisateur ne peut pas dépasser 50 caractères")
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Le nom d'utilisateur ne peut contenir que des lettres, chiffres, tirets et underscores")
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Valider le mot de passe"""
        is_valid, error_message = UserService.validate_password(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str | None
    date_naissance: str | None = None  # Format ISO: YYYY-MM-DD
    telephone: str | None = None
    sexe: str | None = None
    pays_residence: str | None = None
    nationalite: str | None = None
    numero_passeport: str | None = None
    validite_passeport: str | None = None
    nom_contact_urgence: str | None = None
    contact_urgence: str | None = None
    is_active: bool
    role: str
    hospital_id: int | None = None
    hospital_nom: str | None = None
    email_verified: bool = False

    @field_validator("date_naissance", "validite_passeport", mode="before")
    @classmethod
    def coerce_date_to_str(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)

    class Config:
        from_attributes = True


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class ResendVerificationCodeRequest(BaseModel):
    email: EmailStr


class GetMaskedEmailRequest(BaseModel):
    username_or_email: str


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get current authenticated user (raw SQL to avoid enum LookupError on role)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    q = text("""
        SELECT id, username, email, full_name, is_active, hospital_id,
               date_naissance, telephone, sexe, validite_passeport,
               COALESCE(CAST(role AS TEXT), 'user') AS role_str,
               pays_residence, nationalite, numero_passeport,
               nom_contact_urgence, contact_urgence
        FROM users WHERE username = :u LIMIT 1
    """)
    row = db.execute(q, {"u": username}).fetchone()
    if not row:
        raise credentials_exception
    if not row.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    role_str = (row.role_str or "user").lower().strip()
    return SimpleNamespace(
        id=row.id,
        username=row.username,
        email=row.email,
        full_name=row.full_name,
        is_active=row.is_active,
        hospital_id=row.hospital_id,
        date_naissance=row.date_naissance,
        telephone=row.telephone,
        sexe=row.sexe,
        validite_passeport=row.validite_passeport,
        role=role_str,
        pays_residence=getattr(row, "pays_residence", None),
        nationalite=getattr(row, "nationalite", None),
        numero_passeport=getattr(row, "numero_passeport", None),
        nom_contact_urgence=getattr(row, "nom_contact_urgence", None),
        contact_urgence=getattr(row, "contact_urgence", None),
    )


def get_current_user_optional(
    token: str = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
):
    """Get current user if Bearer token is present; otherwise return None (no 401)."""
    if token is None:
        return None
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None
    username: str = payload.get("sub")
    if username is None:
        return None
    q = text("""
        SELECT id, username, email, full_name, is_active, hospital_id,
               date_naissance, telephone, sexe, validite_passeport,
               COALESCE(CAST(role AS TEXT), 'user') AS role_str,
               pays_residence, nationalite, numero_passeport,
               nom_contact_urgence, contact_urgence
        FROM users WHERE username = :u LIMIT 1
    """)
    row = db.execute(q, {"u": username}).fetchone()
    if not row or not row.is_active:
        return None
    role_str = (row.role_str or "user").lower().strip()
    return SimpleNamespace(
        id=row.id,
        username=row.username,
        email=row.email,
        full_name=row.full_name,
        is_active=row.is_active,
        hospital_id=row.hospital_id,
        date_naissance=row.date_naissance,
        telephone=row.telephone,
        sexe=row.sexe,
        validite_passeport=row.validite_passeport,
        role=role_str,
        pays_residence=getattr(row, "pays_residence", None),
        nationalite=getattr(row, "nationalite", None),
        numero_passeport=getattr(row, "numero_passeport", None),
        nom_contact_urgence=getattr(row, "nom_contact_urgence", None),
        contact_urgence=getattr(row, "contact_urgence", None),
    )


def require_admin_user(current_user=Depends(get_current_user)):
    """Require the current user to be an admin"""
    if getattr(current_user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Enregistrer un nouvel utilisateur.

    Le compte est inactif jusqu'à vérification de l'e-mail (code à 6 chiffres).
    Après validation du code via POST /verify-email, le compte est activé.
    """
    
    registration_username = str(user_data.email).strip()
    logger.info(f"Tentative d'inscription: username={registration_username}, email={user_data.email}")

    try:
        # Auto-inscription : is_active=False jusqu'à verify-email
        user = UserService.create_user(
            db=db,
            email=user_data.email,
            username=registration_username,
            password=user_data.password,
            full_name=user_data.full_name,
            date_naissance=user_data.date_naissance,
            telephone=user_data.telephone,
            sexe=user_data.sexe,
            pays_residence=user_data.pays_residence,
            nationalite=user_data.nationalite,
            numero_passeport=user_data.numero_passeport,
            validite_passeport=user_data.validite_passeport,
            nom_contact_urgence=user_data.nom_contact_urgence,
            contact_urgence=user_data.contact_urgence,
            role=Role.USER,
            is_active=False,
            created_by_id=None,
            send_welcome_email=False,
            maladies_chroniques=user_data.maladies_chroniques,
            traitements_en_cours=user_data.traitements_en_cours,
            antecedents_recents=user_data.antecedents_recents,
            grossesse=user_data.grossesse,
        )
        _issue_email_verification_code(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"✓ Utilisateur inscrit avec succès via /register: ID={user.id}, username={user.username}, email={user.email}")
        
        # Vérifier que l'utilisateur est bien dans la base de données
        verify_user = db.query(User).filter(User.id == user.id).first()
        if verify_user:
            logger.info(f"✓ Vérification: Utilisateur {user.username} confirmé dans la base de données (ID: {user.id})")
        else:
            logger.error(f"✗ ERREUR: Utilisateur {user.username} non trouvé dans la base de données après création!")
        
        return user
        
    except HTTPException as e:
        # Ré-élever les exceptions HTTP (erreurs de validation, etc.)
        logger.error(f"✗ Erreur lors de l'inscription de {user_data.username}: {e.detail}")
        raise
    except Exception as e:
        # Capturer toute autre exception
        logger.error(f"✗ Erreur inattendue lors de l'inscription de {user_data.username}: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'inscription: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login and get access/refresh tokens.
    Uses raw SQL for user lookup to avoid SQLAlchemy Enum mismatch (DB stores 'admin', ORM expects 'ADMIN').
    """
    # Récupérer l'utilisateur en SQL brut pour éviter LookupError sur la colonne role (enum)
    q = text("""
        SELECT id, username, email, hashed_password, is_active, validation_inscription,
               COALESCE(email_verified, false) AS email_verified,
               COALESCE(CAST(role AS TEXT), 'user') AS role_str
        FROM users
        WHERE username = :u OR email = :u
        LIMIT 1
    """)
    row = db.execute(q, {"u": form_data.username}).fetchone()
    if not row:
        logger.warning(f"Tentative de connexion avec un identifiant inexistant: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = row.id
    username = row.username
    hashed_password = row.hashed_password
    is_active = row.is_active
    validation_inscription = row.validation_inscription or ""
    email_verified = _sql_bool(getattr(row, "email_verified", None))
    role_value = (row.role_str or "user").lower().strip()

    if not hashed_password:
        logger.error(f"Utilisateur {form_data.username} n'a pas de mot de passe hashé")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User account configuration error"
        )
    try:
        password_valid = verify_password(form_data.password, hashed_password)
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du mot de passe pour {form_data.username}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password verification. Please try again."
        )
    if not password_valid:
        logger.warning(f"Tentative de connexion avec un mot de passe incorrect pour l'utilisateur: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not is_active:
        if validation_inscription == "rejected":
            detail_msg = "Votre inscription a été refusée. Veuillez contacter le service client."
        elif not email_verified:
            detail_msg = (
                "Veuillez saisir le code de vérification reçu par e-mail pour activer votre compte."
            )
        elif validation_inscription == "approved" and email_verified:
            db.execute(
                text("UPDATE users SET is_active = true WHERE id = :id"),
                {"id": user_id},
            )
            db.commit()
            is_active = True
            logger.info(f"Compte auto-activé à la connexion (e-mail déjà vérifié): {username}")
        elif validation_inscription == "pending":
            detail_msg = (
                "Votre inscription est en cours de validation. Vous recevrez un e-mail lorsque votre compte sera activé."
            )
        else:
            detail_msg = "Compte désactivé. Contactez le service client."

        if not is_active:
            logger.warning(f"Tentative de connexion compte non actif: {form_data.username} (validation_inscription={validation_inscription})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail_msg
            )
    try:
        if not settings.SECRET_KEY or settings.SECRET_KEY == "your-secret-key-change-in-production":
            logger.error("SECRET_KEY n'est pas configuré correctement")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error"
            )
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username, "role": role_value},
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(
            data={"sub": username, "role": role_value}
        )
        try:
            redis = get_redis()
            if redis is not None:
                try:
                    redis.setex(
                        f"refresh_token:{user_id}",
                        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                        refresh_token
                    )
                except Exception as redis_error:
                    logger.error(f"Erreur lors du stockage du refresh token dans Redis: {redis_error}")
            else:
                logger.warning("Redis non disponible - le refresh token ne sera pas stocké")
        except Exception as redis_init_error:
            logger.warning(f"Redis non disponible (erreur d'initialisation): {redis_init_error}")
        logger.info(f"Connexion réussie pour l'utilisateur: {username} (ID: {user_id})")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création des tokens pour {form_data.username}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login. Please try again."
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token (raw SQL to avoid enum error)."""
    payload = decode_token(token_data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    q = text("SELECT id, username, is_active, COALESCE(CAST(role AS TEXT), 'user') AS role_str FROM users WHERE username = :u LIMIT 1")
    row = db.execute(q, {"u": username}).fetchone()
    if not row or not row.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    user_id, username, is_active, role_str = row.id, row.username, row.is_active, (row.role_str or "user").lower().strip()
    try:
        redis = get_redis()
        if redis is not None:
            stored_token = redis.get(f"refresh_token:{user_id}")
            if stored_token and stored_token != token_data.refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token not found or expired"
                )
    except HTTPException:
        raise
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible lors de la vérification du refresh token: {redis_init_error}")
    minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)
    access_token = create_access_token(
        data={"sub": username, "role": role_str},
        expires_delta=timedelta(minutes=minutes)
    )
    new_refresh_token = create_refresh_token(data={"sub": username, "role": role_str})
    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis.setex(f"refresh_token:{user_id}", days * 24 * 60 * 60, new_refresh_token)
            except Exception as e:
                logger.warning(f"Erreur lors de la mise à jour du refresh token dans Redis: {e}")
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible lors de la mise à jour du refresh token: {redis_init_error}")
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    current_user=Depends(get_current_user)
):
    """Logout and invalidate refresh token"""
    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis.delete(f"refresh_token:{current_user.id}")
            except Exception as e:
                logger.warning(f"Erreur lors de la suppression du refresh token dans Redis: {e}")
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible lors du logout: {redis_init_error}")
    return {"message": "Successfully logged out"}


class FcmTokenUpdate(BaseModel):
    """Jeton FCM de l’appareil (Firebase Cloud Messaging) pour les notifications push."""

    fcm_registration_token: str


@router.put("/me/fcm-token")
async def register_fcm_token(
    body: FcmTokenUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enregistrer ou mettre à jour le jeton push de l’app mobile (médecin référent, assuré, etc.).
    À appeler après connexion une fois Firebase Messaging initialisé.
    """
    token = (body.fcm_registration_token or "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fcm_registration_token requis",
        )
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    user.fcm_registration_token = token
    db.commit()
    return {"ok": True, "message": "Jeton FCM enregistré"}


@router.delete("/me/fcm-token")
async def clear_fcm_token(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprimer le jeton (ex. déconnexion de l’app)."""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    user.fcm_registration_token = None
    db.commit()
    return {"ok": True, "message": "Jeton FCM supprimé"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user information"""
    date_naissance_str = None
    if getattr(current_user, "date_naissance", None):
        d = current_user.date_naissance
        date_naissance_str = d.isoformat() if hasattr(d, "isoformat") else str(d)
    validite_passeport_str = None
    if getattr(current_user, "validite_passeport", None):
        v = current_user.validite_passeport
        validite_passeport_str = v.isoformat() if hasattr(v, "isoformat") else str(v)
    hospital_nom = None
    if getattr(current_user, "hospital_id", None):
        hospital = db.query(Hospital).filter(Hospital.id == current_user.hospital_id).first()
        if hospital:
            hospital_nom = hospital.nom
    role_str = getattr(current_user, "role", "user")
    if hasattr(role_str, "value"):
        role_str = role_str.value
    role_str = str(role_str) if role_str else "user"
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "date_naissance": date_naissance_str,
        "telephone": getattr(current_user, "telephone", None),
        "sexe": getattr(current_user, "sexe", None),
        "pays_residence": getattr(current_user, "pays_residence", None),
        "nationalite": getattr(current_user, "nationalite", None),
        "numero_passeport": getattr(current_user, "numero_passeport", None),
        "validite_passeport": validite_passeport_str,
        "nom_contact_urgence": getattr(current_user, "nom_contact_urgence", None),
        "contact_urgence": getattr(current_user, "contact_urgence", None),
        "is_active": current_user.is_active,
        "role": role_str,
        "hospital_id": getattr(current_user, "hospital_id", None),
        "hospital_nom": hospital_nom,
    }


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """Request password reset - sends reset code to email"""
    user = db.query(User).filter(User.email == request.email).first()
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If the email exists, a reset code has been sent"}
    
    # Vérifier si l'utilisateur est bloqué (trop de tentatives)
    try:
        redis = get_redis()
        if redis is not None:
            try:
                block_key = f"password_reset_block:{user.id}"
                blocked_until = redis.get(block_key)
                if blocked_until:
                    import time
                    blocked_until_ts = float(blocked_until)
                    remaining_time = int(blocked_until_ts - time.time())
                    if remaining_time > 0:
                        hours = remaining_time // 3600
                        minutes = (remaining_time % 3600) // 60
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Trop de tentatives. Veuillez réessayer dans {hours}h {minutes}min."
                        )
                    else:
                        # Le blocage est expiré, le supprimer
                        redis.delete(block_key)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du blocage: {e}")
    except HTTPException:
        raise
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible (erreur d'initialisation): {redis_init_error}")
    
    # Vérifier s'il y a déjà un code actif (pour éviter le spam)
    try:
        redis = get_redis()
        if redis is not None:
            try:
                active_code_key = f"password_reset_active:{user.id}"
                active_code = redis.get(active_code_key)
                if active_code:
                    # Il y a déjà un code actif, retourner un message mais ne pas renvoyer
                    return {
                        "message": "If the email exists, a reset code has been sent",
                        "code_already_sent": True
                    }
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du code actif: {e}")
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible: {redis_init_error}")
    
    # Generate 6-digit code
    reset_code = ''.join(random.choices(string.digits, k=6))
    
    # Store code in Redis with 10 minutes expiry
    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis_key = f"password_reset:{user.id}:{reset_code}"
                redis.setex(redis_key, 600, user.email)  # 10 minutes
                
                # Also store by email for lookup
                redis_email_key = f"password_reset_email:{request.email}"
                redis.setex(redis_email_key, 600, reset_code)
                
                # Marquer qu'un code est actif
                active_code_key = f"password_reset_active:{user.id}"
                redis.setex(active_code_key, 600, reset_code)  # 10 minutes
                
                # Réinitialiser le compteur de tentatives
                attempts_key = f"password_reset_attempts:{user.id}"
                redis.setex(attempts_key, 600, "0")  # 10 minutes
            except Exception as e:
                logger.error(f"Erreur lors du stockage du code de réinitialisation dans Redis: {e}")
                # En mode dégradé, on continue sans Redis
        else:
            logger.warning("Redis non disponible - le code de réinitialisation ne sera pas stocké")
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible (erreur d'initialisation): {redis_init_error}")
    
    # Envoyer l'email de réinitialisation
    try:
        UserService.send_password_reset_email(user, reset_code)
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email de réinitialisation: {str(e)}")
        # Ne pas faire échouer la requête si l'email échoue (pour éviter l'énumération d'emails)
        # En développement, on peut logger le code
        if settings.DEBUG or settings.ENVIRONMENT == "development":
            logger.info(f"Password reset code for {request.email}: {reset_code}")
    
    return {"message": "If the email exists, a reset code has been sent"}


@router.post("/verify-reset-code")
async def verify_reset_code(
    request: VerifyResetCodeRequest,
    db: Session = Depends(get_db)
):
    """Verify password reset code"""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Vérifier si l'utilisateur est bloqué
    try:
        redis = get_redis()
        if redis is not None:
            try:
                block_key = f"password_reset_block:{user.id}"
                blocked_until = redis.get(block_key)
                if blocked_until:
                    import time
                    blocked_until_ts = float(blocked_until)
                    remaining_time = int(blocked_until_ts - time.time())
                    if remaining_time > 0:
                        hours = remaining_time // 3600
                        minutes = (remaining_time % 3600) // 60
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Trop de tentatives. Veuillez réessayer dans {hours}h {minutes}min."
                        )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du blocage: {e}")
    except HTTPException:
        raise
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible: {redis_init_error}")
    
    # Vérifier le nombre de tentatives
    attempts_key = f"password_reset_attempts:{user.id}"
    max_attempts = 5
    block_duration = 7200  # 2 heures en secondes
    
    # Check code in Redis
    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis_email_key = f"password_reset_email:{request.email}"
                stored_code = redis.get(redis_email_key)
                
                if not stored_code or stored_code != request.code:
                    # Code invalide, incrémenter les tentatives
                    current_attempts = redis.get(attempts_key)
                    attempts = int(current_attempts) if current_attempts else 0
                    attempts += 1
                    
                    if attempts >= max_attempts:
                        # Bloquer l'utilisateur pendant 2 heures
                        import time
                        block_key = f"password_reset_block:{user.id}"
                        redis.setex(block_key, block_duration, str(time.time() + block_duration))
                        redis.delete(attempts_key)
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Trop de tentatives échouées. Veuillez réessayer dans 2 heures."
                        )
                    else:
                        # Mettre à jour le compteur de tentatives
                        ttl = redis.ttl(redis_email_key)  # Récupérer le TTL restant
                        if ttl > 0:
                            redis.setex(attempts_key, ttl, str(attempts))
                        else:
                            redis.setex(attempts_key, 600, str(attempts))  # 10 minutes par défaut
                        
                        remaining_attempts = max_attempts - attempts
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Code invalide. Il vous reste {remaining_attempts} tentative(s)."
                        )
                
                # Code valide, réinitialiser les tentatives
                redis.delete(attempts_key)
                
                # Generate a token for password reset (valid for 15 minutes)
                reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
                redis_token_key = f"password_reset_token:{request.email}"
                redis.setex(redis_token_key, 900, reset_token)  # 15 minutes
                
                # Delete the code to prevent reuse
                redis.delete(redis_email_key)
                redis.delete(f"password_reset:{user.id}:{request.code}")
                redis.delete(f"password_reset_active:{user.id}")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du code dans Redis: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An error occurred during code verification"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Password reset service is temporarily unavailable"
            )
    except HTTPException:
        raise
    except Exception as redis_init_error:
        logger.error(f"Redis non disponible (erreur d'initialisation): {redis_init_error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset service is temporarily unavailable"
        )
    
    return {"token": reset_token, "message": "Code verified successfully"}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password with token"""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify token
    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis_token_key = f"password_reset_token:{request.email}"
                stored_token = redis.get(redis_token_key)
                
                if not stored_token or stored_token != request.token:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid or expired reset token"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du token dans Redis: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An error occurred during token verification"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Password reset service is temporarily unavailable"
            )
    except HTTPException:
        raise
    except Exception as redis_init_error:
        logger.error(f"Redis non disponible (erreur d'initialisation): {redis_init_error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset service is temporarily unavailable"
        )
    
    # Validate password using service
    is_valid, error_message = UserService.validate_password(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    
    # Delete token to prevent reuse
    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis_token_key = f"password_reset_token:{request.email}"
                redis.delete(redis_token_key)
                
                # Invalidate all refresh tokens for security
                redis.delete(f"refresh_token:{user.id}")
            except Exception as e:
                logger.warning(f"Erreur lors de la suppression des tokens dans Redis: {e}")
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible lors de la suppression des tokens: {redis_init_error}")
    
    return {"message": "Password reset successfully"}


@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """Vérifier l'e-mail avec le code ; active le compte (flux inscription standard)."""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    if user.is_active and user.email_verified:
        return {"message": "Compte déjà activé"}

    if user.email_verified and not user.is_active:
        vi = getattr(user, "validation_inscription", None) or ""
        if vi == "rejected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inscription refusée. L'activation est impossible.",
            )
        if vi == "approved":
            user.is_active = True
            db.commit()
            logger.info(f"Compte activé (e-mail déjà vérifié): {user.username} ({user.email})")
            return {"message": "Compte activé. Vous pouvez vous connecter."}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cette adresse e-mail est déjà vérifiée. Votre compte est en attente de validation."
            ),
        )

    # Vérifier le code dans Redis
    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis_email_key = f"email_verification_email:{request.email}"
                stored_code = redis.get(redis_email_key)
                
                if not stored_code or stored_code != request.code:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Code de vérification invalide ou expiré"
                    )
                
                user.email_verified = True
                user.validation_inscription = "approved"
                user.is_active = True
                db.commit()
                
                # Supprimer le code pour éviter la réutilisation
                redis.delete(redis_email_key)
                redis.delete(f"email_verification:{user.id}:{request.code}")
                
                logger.info(f"Compte activé après vérification e-mail: {user.username} ({user.email})")
                
                return {
                    "message": "Compte activé. Vous pouvez vous connecter.",
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du code dans Redis: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Une erreur est survenue lors de la vérification du code"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service de vérification temporairement indisponible"
            )
    except HTTPException:
        raise
    except Exception as redis_init_error:
        logger.error(f"Redis non disponible (erreur d'initialisation): {redis_init_error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service de vérification temporairement indisponible"
        )


@router.get("/verify-email-link")
async def verify_email_link(
    token: str = Query(..., description="Jeton reçu dans l'e-mail de vérification"),
    db: Session = Depends(get_db),
):
    """Active le compte en un clic (bouton ou lien dans l'e-mail). Redirige vers le site (login)."""
    site_base = (getattr(settings, "ASSURANCE_SITE_WEB", "") or "").strip().rstrip("/")

    def redirect_ok(message: str) -> RedirectResponse:
        if not site_base:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ASSURANCE_SITE_WEB non configuré : impossible de rediriger après vérification.",
            )
        url = f"{site_base}/login.html?verified=1&message={quote_plus(message)}"
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)

    def redirect_err(message: str) -> RedirectResponse:
        if not site_base:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        url = f"{site_base}/login.html?verify_link_error=1&message={quote_plus(message)}"
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)

    decoded = decode_email_verification_token(token)
    if not decoded:
        return redirect_err(
            "Lien invalide ou expiré. Réessayez depuis la page de vérification ou demandez un nouveau code."
        )

    user_id, email_norm = decoded
    user = db.query(User).filter(User.id == user_id).first()
    if not user or (user.email or "").strip().lower() != email_norm:
        return redirect_err("Lien invalide. Demandez un nouveau code de vérification.")

    if user.is_active and user.email_verified:
        return redirect_ok("Votre compte est déjà activé. Vous pouvez vous connecter.")

    if user.email_verified and not user.is_active:
        vi = getattr(user, "validation_inscription", None) or ""
        if vi == "rejected":
            return redirect_err("Inscription refusée. L'activation est impossible.")
        return redirect_err(
            "Ce compte nécessite une autre étape d'activation. Consultez vos e-mails ou contactez le support."
        )

    user.email_verified = True
    user.validation_inscription = "approved"
    user.is_active = True
    db.commit()

    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis.delete(f"email_verification_email:{user.email}")
            except Exception as e:
                logger.warning("Redis cleanup après lien e-mail: %s", e)
    except Exception:
        pass

    logger.info("Compte activé via lien e-mail pour user_id=%s", user.id)
    return redirect_ok("Compte activé. Vous pouvez vous connecter.")


@router.get("/confirm-inscription")
async def confirm_inscription(
    token: str = Query(..., description="Token d'activation finale d'inscription"),
    db: Session = Depends(get_db),
):
    """Ancien flux : activer un compte déjà approuvé (lien e-mail). Les nouvelles inscriptions passent par /verify-email."""
    site_base = (getattr(settings, "ASSURANCE_SITE_WEB", "") or "").strip().rstrip("/")

    def build_redirect(status_value: str, message: str) -> RedirectResponse:
        if site_base:
            url = f"{site_base}/confirm-inscription.html?status={quote_plus(status_value)}&message={quote_plus(message)}"
            return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    user_id = decode_inscription_activation_token(token)
    if user_id is None:
        return build_redirect("error", "Lien d'activation invalide ou expiré.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return build_redirect("error", "Utilisateur introuvable.")

    current_status = getattr(user, "validation_inscription", None)
    if current_status == "rejected":
        return build_redirect("error", "Votre inscription a été refusée. L'activation est impossible.")
    if current_status != "approved":
        return build_redirect("error", "Votre inscription n'est pas encore approuvée.")
    if user.is_active:
        return build_redirect("already_active", "Votre compte est déjà activé. Vous pouvez vous connecter sur l'application mobile.")

    user.is_active = True
    user.email_verified = True
    db.commit()

    logger.info("Compte activé via lien email pour user_id=%s", user.id)
    return build_redirect("success", "Votre compte est maintenant activé. Vous pouvez vous connecter sur l'application mobile.")


@router.post("/resend-verification-code")
async def resend_verification_code(
    request: ResendVerificationCodeRequest,
    db: Session = Depends(get_db)
):
    """Renvoyer le code de vérification par email"""
    user = db.query(User).filter(User.email == request.email).first()
    
    # Toujours retourner un succès pour éviter l'énumération d'emails
    if not user:
        return {"message": "Si cet email existe, un code de vérification a été envoyé"}
    
    if user.is_active:
        return {"message": "Compte déjà activé"}

    if user.email_verified and not user.is_active:
        # Ancien flux (e-mail déjà marqué vérifié avant activation) : ne pas envoyer de code piège
        return {"message": "Si cet email existe, un code de vérification a été envoyé"}
    
    _issue_email_verification_code(user)
    
    return {"message": "Si cet email existe, un code de vérification a été envoyé"}


@router.post("/get-masked-email")
async def get_masked_email(
    request: GetMaskedEmailRequest,
    db: Session = Depends(get_db)
):
    """Récupérer l'email masqué depuis un username ou email"""
    # Chercher l'utilisateur par username ou email
    user = db.query(User).filter(
        (User.username == request.username_or_email) | (User.email == request.username_or_email)
    ).first()
    
    # Toujours retourner un résultat pour éviter l'énumération
    if not user:
        # Retourner un email masqué fictif pour éviter l'énumération
        if '@' in request.username_or_email:
            # C'est déjà un email, le masquer
            email_parts = request.username_or_email.split('@')
            if len(email_parts) == 2:
                local_part = email_parts[0]
                domain = email_parts[1]
                masked_local = local_part[:2] + '***' if len(local_part) > 2 else '***'
                masked_email = f"{masked_local}@{domain}"
                return {"masked_email": masked_email, "exists": False}
        return {"masked_email": "***@***", "exists": False}
    
    # Masquer l'email réel
    email_parts = user.email.split('@')
    if len(email_parts) == 2:
        local_part = email_parts[0]
        domain = email_parts[1]
        # Afficher les 2 premiers caractères, puis ***
        masked_local = local_part[:2] + '***' if len(local_part) > 2 else '***'
        masked_email = f"{masked_local}@{domain}"
        return {"masked_email": masked_email, "email": user.email, "exists": True}
    
    return {"masked_email": "***@***", "exists": False}

