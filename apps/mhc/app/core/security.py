from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        # Try passlib first
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, Exception):
        # Fallback to bcrypt directly if passlib fails
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except (ValueError, Exception) as e:
            # Handle bcrypt errors (e.g., password too long, invalid hash)
            print(f"Password verification error: {e}")
            return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    try:
        # Try passlib first
        return pwd_context.hash(password)
    except (ValueError, Exception):
        # Fallback to bcrypt directly if passlib fails
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _get_algorithm() -> str:
    return getattr(settings, "ALGORITHM", "HS256")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30)
        expire = datetime.utcnow() + timedelta(minutes=minutes)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=_get_algorithm())
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)
    expire = datetime.utcnow() + timedelta(days=days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=_get_algorithm())
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_get_algorithm()])
        return payload
    except JWTError:
        return None


def create_ecard_access_token(attestation_id: int, expires_minutes: int = 30) -> str:
    """Create a short-lived JWT for e-card image/download access (for img src without Bearer)."""
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode = {"sub": str(attestation_id), "type": "ecard", "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=_get_algorithm())


def decode_ecard_token(token: str) -> Optional[int]:
    """Decode e-card token and return attestation_id if valid, else None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_get_algorithm()])
        if payload.get("type") != "ecard":
            return None
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (JWTError, ValueError, TypeError):
        return None


def create_download_access_token(resource_type: str, resource_id: int, expires_minutes: int = 30) -> str:
    """Create a short-lived JWT for direct download/view of protected resources."""
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode = {
        "sub": str(resource_id),
        "type": "download",
        "resource_type": resource_type,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=_get_algorithm())


def decode_download_access_token(token: str, expected_resource_type: str) -> Optional[int]:
    """Decode a download token and return resource id if valid and of expected type."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_get_algorithm()])
        if payload.get("type") != "download":
            return None
        if payload.get("resource_type") != expected_resource_type:
            return None
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (JWTError, ValueError, TypeError):
        return None


def create_inscription_activation_token(user_id: int, expires_hours: int = 72) -> str:
    """Create a short-lived token used to activate an approved registration."""
    expire = datetime.utcnow() + timedelta(hours=expires_hours)
    to_encode = {"sub": str(user_id), "type": "inscription_activation", "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=_get_algorithm())


def decode_inscription_activation_token(token: str) -> Optional[int]:
    """Decode inscription activation token and return user id if valid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_get_algorithm()])
        if payload.get("type") != "inscription_activation":
            return None
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (JWTError, ValueError, TypeError):
        return None


def create_email_verification_token(user_id: int, email: str, expires_minutes: int = 15) -> str:
    """JWT pour lien « un clic » dans l'e-mail de vérification (même durée que le code Redis)."""
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    normalized = (email or "").strip().lower()
    to_encode = {
        "sub": str(user_id),
        "email": normalized,
        "type": "email_verification",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=_get_algorithm())


def decode_email_verification_token(token: str) -> Optional[Tuple[int, str]]:
    """Retourne (user_id, email_normalisé) si le jeton est valide."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_get_algorithm()])
        if payload.get("type") != "email_verification":
            return None
        sub = payload.get("sub")
        email = payload.get("email")
        if sub is None or not email:
            return None
        return int(sub), str(email).strip().lower()
    except (JWTError, ValueError, TypeError):
        return None

