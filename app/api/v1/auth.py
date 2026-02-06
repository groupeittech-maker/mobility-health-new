from datetime import timedelta
import random
import string
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.config import settings
from app.core.redis_client import get_redis
from app.core.enums import Role
from app.models.user import User
from app.models.hospital import Hospital
from app.services.user_service import UserService
from pydantic import BaseModel, EmailStr, field_validator

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
logger = logging.getLogger(__name__)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    username: str
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
    # Informations médicales à l'inscription
    maladies_chroniques: str | None = None   # diabète, HTA, asthme, épilepsie, drépanocytose, cardiopathie, etc.
    traitements_en_cours: str | None = None  # médicaments réguliers
    antecedents_recents: str | None = None   # hospitalisation, chirurgie, suivi < 6 mois
    grossesse: bool | None = None             # si concernée
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Valider le nom d'utilisateur"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Le nom d'utilisateur ne peut pas être vide")
        if len(v) < 3:
            raise ValueError("Le nom d'utilisateur doit contenir au moins 3 caractères")
        if len(v) > 50:
            raise ValueError("Le nom d'utilisateur ne peut pas dépasser 50 caractères")
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Le nom d'utilisateur ne peut contenir que des lettres, chiffres, tirets et underscores")
        return v.strip()
    
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
) -> User:
    """Get current authenticated user"""
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
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    return user


def require_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be an admin"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Enregistrer un nouvel utilisateur.
    
    Pas de validation par email en pré-production : l'inscription est en attente de validation
    par le médecin MH. Une fois validée, l'abonné peut se connecter pour souscrire.
    """
    
    logger.info(f"Tentative d'inscription: username={user_data.username}, email={user_data.email}")
    
    try:
        # Utiliser le service pour créer l'utilisateur
        # created_by_id=None car c'est une auto-inscription
        # is_active=False jusqu'à validation par le médecin MH
        user = UserService.create_user(
            db=db,
            email=user_data.email,
            username=user_data.username,
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
        # Pas de validation par email pour l'instant (hors production) : considérer l'email comme vérifié
        # pour que l'utilisateur apparaisse dans la liste des inscriptions en attente du médecin MH
        user.email_verified = True
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
    
    Accepts form data with 'username' and 'password' fields.
    """
    
    # Rechercher l'utilisateur par username ou email
    # Le champ 'username' dans OAuth2PasswordRequestForm peut contenir soit un username soit un email
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()
    
    # Vérifier si l'utilisateur existe
    if not user:
        logger.warning(f"Tentative de connexion avec un identifiant inexistant: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Vérifier le mot de passe
    try:
        if not user.hashed_password:
            logger.error(f"Utilisateur {form_data.username} n'a pas de mot de passe hashé")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User account configuration error"
            )
        password_valid = verify_password(form_data.password, user.hashed_password)
    except HTTPException:
        raise
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
    
    # Vérifier si l'utilisateur peut se connecter (inscription validée par le médecin MH)
    if not user.is_active:
        validation_inscription = getattr(user, "validation_inscription", None) or ""
        if validation_inscription == "rejected":
            detail_msg = "Votre inscription a été refusée par le médecin MH. Veuillez contacter le service client."
        elif validation_inscription == "pending":
            detail_msg = "Votre inscription est en cours de validation par le médecin MH. Vous recevrez un email lorsque votre compte sera activé."
        else:
            detail_msg = "Votre email n'a pas été vérifié. Veuillez vérifier votre email avant de vous connecter."
        logger.warning(f"Tentative de connexion compte non actif: {form_data.username} (validation_inscription={validation_inscription})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail_msg
        )
    
    try:
        # Create tokens
        # Gérer le rôle de manière sécurisée
        try:
            role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
        except Exception as role_error:
            logger.error(f"Erreur lors de l'extraction du rôle pour {form_data.username}: {role_error}", exc_info=True)
            role_value = "user"  # Valeur par défaut
        
        if not settings.SECRET_KEY or settings.SECRET_KEY == "your-secret-key-change-in-production":
            logger.error("SECRET_KEY n'est pas configuré correctement")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error"
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "role": role_value},
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(
            data={"sub": user.username, "role": role_value}
        )
        
        # Store refresh token in Redis (avec gestion d'erreur gracieuse)
        try:
            redis = get_redis()
            if redis is not None:
                try:
                    redis.setex(
                        f"refresh_token:{user.id}",
                        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                        refresh_token
                    )
                except Exception as redis_error:
                    # Si Redis échoue, on log l'erreur mais on continue quand même
                    # Le refresh token ne sera pas stocké, mais l'utilisateur peut toujours utiliser l'access token
                    logger.error(f"Erreur lors du stockage du refresh token dans Redis: {redis_error}")
                    # En développement, on peut continuer sans Redis
            else:
                logger.warning("Redis non disponible - le refresh token ne sera pas stocké")
        except Exception as redis_init_error:
            # Si get_redis() lève une exception (ex: RuntimeError en production), on continue sans Redis
            logger.warning(f"Redis non disponible (erreur d'initialisation): {redis_init_error}")
        
        logger.info(f"Connexion réussie pour l'utilisateur: {user.username} (ID: {user.id})")
        
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
    """Refresh access token using refresh token"""
    payload = decode_token(token_data.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    username: str = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Verify refresh token is in Redis
    try:
        redis = get_redis()
        if redis is not None:
            stored_token = redis.get(f"refresh_token:{user.id}")
            if stored_token and stored_token != token_data.refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token not found or expired"
                )
        # Si Redis n'est pas disponible, on accepte le token (mode dégradé)
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible lors de la vérification du refresh token: {redis_init_error}")
    
    # Create new tokens
    # Gérer le rôle de manière sécurisée
    role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": role_value},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "role": role_value}
    )
    
    # Update refresh token in Redis
    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis.setex(
                    f"refresh_token:{user.id}",
                    settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                    refresh_token
                )
            except Exception as e:
                logger.warning(f"Erreur lors de la mise à jour du refresh token dans Redis: {e}")
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible lors de la mise à jour du refresh token: {redis_init_error}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
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


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user information"""
    date_naissance_str = None
    if current_user.date_naissance:
        date_naissance_str = current_user.date_naissance.isoformat()
    validite_passeport_str = None
    if getattr(current_user, 'validite_passeport', None):
        validite_passeport_str = current_user.validite_passeport.isoformat()

    hospital_nom = None
    if current_user.hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == current_user.hospital_id).first()
        if hospital:
            hospital_nom = hospital.nom

    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "date_naissance": date_naissance_str,
        "telephone": current_user.telephone,
        "sexe": current_user.sexe,
        "pays_residence": getattr(current_user, 'pays_residence', None),
        "nationalite": getattr(current_user, 'nationalite', None),
        "numero_passeport": getattr(current_user, 'numero_passeport', None),
        "validite_passeport": validite_passeport_str,
        "nom_contact_urgence": getattr(current_user, 'nom_contact_urgence', None),
        "contact_urgence": getattr(current_user, 'contact_urgence', None),
        "is_active": current_user.is_active,
        "role": current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        "hospital_id": current_user.hospital_id,
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
    """Vérifier l'email avec le code de vérification"""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    if user.is_active:
        return {"message": "Email déjà vérifié"}
    
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
                
                # Marquer l'email comme vérifié ; l'utilisateur reste inactif jusqu'à validation par le médecin MH
                user.email_verified = True
                if getattr(user, 'validation_inscription', None) is None:
                    user.validation_inscription = "pending"
                db.commit()
                
                # Supprimer le code pour éviter la réutilisation
                redis.delete(redis_email_key)
                redis.delete(f"email_verification:{user.id}:{request.code}")
                
                logger.info(f"Email vérifié pour l'utilisateur: {user.username} ({user.email})")
                
                return {"message": "Email vérifié. Votre inscription est en cours de validation par le médecin MH. Vous recevrez un email lorsque votre compte sera activé."}
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
        return {"message": "Email déjà vérifié"}
    
    # Générer un nouveau code de vérification
    verification_code = ''.join(random.choices(string.digits, k=6))
    
    # Stocker le code dans Redis avec expiration de 15 minutes
    try:
        redis = get_redis()
        if redis is not None:
            try:
                redis_key = f"email_verification:{user.id}:{verification_code}"
                redis.setex(redis_key, 900, user.email)  # 15 minutes
                
                # Aussi stocker par email pour lookup
                redis_email_key = f"email_verification_email:{user.email}"
                redis.setex(redis_email_key, 900, verification_code)
            except Exception as e:
                logger.error(f"Erreur lors du stockage du code de vérification dans Redis: {e}")
        else:
            logger.warning("Redis non disponible - le code de vérification ne sera pas stocké")
    except Exception as redis_init_error:
        logger.warning(f"Redis non disponible (erreur d'initialisation): {redis_init_error}")
    
    # Envoyer l'email de vérification
    try:
        UserService.send_verification_email(user, verification_code)
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email de vérification: {str(e)}")
    
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

