from typing import List, Union
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.enums import Role
from app.core.security import get_password_hash
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.services.user_service import UserService
from app.models.attestation import Attestation
from app.models.souscription import Souscription
from app.schemas.attestation import AttestationResponse
from pydantic import BaseModel, EmailStr, field_serializer

router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str | None = None
    pays_residence: str | None = None
    role: Role = Role.USER
    is_active: bool = True
    role_id: int | None = None
    hospital_id: int | None = None


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    pays_residence: str | None = None
    is_active: bool | None = None
    role: Role | None = None
    hospital_id: int | None = None


class UserPasswordReset(BaseModel):
    new_password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str | None
    pays_residence: str | None = None
    is_active: bool
    role: str
    hospital_id: int | None = None
    email_verified: bool | None = None
    validation_inscription: str | None = None
    validation_inscription_date: datetime | None = None
    # Informations civiles (pour consultation par le médecin MH avant validation)
    date_naissance: Union[date, str, None] = None
    telephone: str | None = None
    sexe: str | None = None
    nationalite: str | None = None
    numero_passeport: str | None = None
    validite_passeport: Union[date, str, None] = None
    nom_contact_urgence: str | None = None
    contact_urgence: str | None = None
    created_at: Union[datetime, str, None] = None
    # Informations médicales (inscription)
    maladies_chroniques: str | None = None
    traitements_en_cours: str | None = None
    antecedents_recents: str | None = None
    grossesse: bool | None = None

    @field_serializer("date_naissance", "validite_passeport", "created_at", "validation_inscription_date", when_used="always")
    def serialize_date_datetime(self, v):
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)

    class Config:
        from_attributes = True


class ValidateInscriptionRequest(BaseModel):
    approved: bool
    notes: str | None = None


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    role: Role | None = None,
    search: str | None = None,
    hospital_id: int | None = None,
    validation_inscription: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Liste des utilisateurs.
    Admin : tous les utilisateurs.
    Médecin MH (medical_reviewer) : peut filtrer par validation_inscription=pending pour les inscriptions en attente.
    """
    is_admin = current_user.role == Role.ADMIN
    is_medical_reviewer = (current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)) == "medical_reviewer"
    if not is_admin and not is_medical_reviewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    if is_medical_reviewer and not is_admin:
        if validation_inscription != "pending":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Médecin MH peut uniquement consulter les inscriptions en attente (validation_inscription=pending)"
            )

    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if validation_inscription:
        query = query.filter(User.validation_inscription == validation_inscription)
        if validation_inscription == "pending":
            query = query.filter(User.email_verified == True)
            query = query.filter(User.role == Role.USER)
    if hospital_id is not None:
        query = query.filter(User.hospital_id == hospital_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.username.ilike(pattern)
            )
        )
    
    # Trier par date de création (plus récents en premier), puis par nom complet et username
    # Cela permet de voir les nouveaux utilisateurs inscrits en premier
    users = query.order_by(
        User.created_at.desc(),
        User.full_name.asc().nulls_last(),
        User.username.asc()
    ).offset(skip).limit(limit).all()
    
    # Log pour débogage avec détails
    import logging
    logger = logging.getLogger(__name__)
    total_count = query.count()  # Compter le total sans pagination
    logger.info(f"Liste des utilisateurs récupérée: {len(users)}/{total_count} utilisateurs (skip={skip}, limit={limit})")
    
    # Log les usernames pour débogage (premiers 10)
    if users:
        usernames = [u.username for u in users[:10]]
        logger.debug(f"Premiers utilisateurs dans la liste: {', '.join(usernames)}")
    
    return users


# Autoriser également l'URL sans slash final (/users) afin d'éviter les redirections 307 côté navigateur.
router.add_api_route(
    "",
    get_users,
    methods=["GET"],
    include_in_schema=False,
)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Créer un nouvel utilisateur (admin uniquement).
    
    Utilise le service UserService pour une validation complète et l'envoi d'email de bienvenue.
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Utiliser le service pour créer l'utilisateur
    # Le service gère toutes les validations et l'envoi de l'email de bienvenue
    # created_by_id = current_user.id car c'est l'admin qui crée l'utilisateur
    user = UserService.create_user(
        db=db,
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name,
        pays_residence=user_data.pays_residence,
        role=user_data.role,
        is_active=user_data.is_active,
        role_id=user_data.role_id,
        hospital_id=user_data.hospital_id,
        created_by_id=current_user.id,  # Lien avec l'admin qui crée le compte
        send_welcome_email=True
    )

    return user


# Autoriser également l'URL sans slash final
router.add_api_route(
    "",
    create_user,
    methods=["POST"],
    include_in_schema=False,
)


@router.get("/me/attestations", response_model=List[AttestationResponse])
async def get_my_attestations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtenir toutes les attestations associées à l'utilisateur connecté."""
    attestations = (
        db.query(Attestation)
        .join(Souscription, Attestation.souscription_id == Souscription.id)
        .filter(Souscription.user_id == current_user.id)
        .order_by(Attestation.created_at.desc())
        .all()
    )
    return attestations

@router.get("/search/{username}", response_model=UserResponse)
async def search_user_by_username(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rechercher un utilisateur par nom d'utilisateur (admin only)"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username '{username}' not found"
        )
    
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user by ID (soi-même, admin, ou médecin MH pour une inscription en attente)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    is_admin = current_user.role == Role.ADMIN
    is_medical_reviewer = (current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)) == "medical_reviewer"
    if current_user.id != user_id and not is_admin:
        if is_medical_reviewer and getattr(user, "validation_inscription", None) == "pending":
            pass  # Médecin MH peut voir une inscription en attente
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    return user


@router.post("/{user_id}/validate_inscription", response_model=UserResponse)
async def validate_inscription(
    user_id: int,
    body: ValidateInscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Valider ou refuser une inscription (médecin MH ou admin).
    Si approuvée : l'utilisateur peut se connecter et souscrire.
    """
    is_admin = current_user.role == Role.ADMIN
    is_medical_reviewer = (current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)) == "medical_reviewer"
    if not is_admin and not is_medical_reviewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le médecin MH ou l'admin peut valider une inscription"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")
    if getattr(user, "validation_inscription", None) != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette inscription n'est pas en attente de validation"
        )
    user.validation_inscription = "approved" if body.approved else "rejected"
    user.validation_inscription_par = current_user.id
    user.validation_inscription_date = datetime.utcnow()
    user.validation_inscription_notes = body.notes
    if body.approved:
        user.is_active = True
    db.add(
        Notification(
            user_id=user.id,
            type_notification="inscription_validation_result",
            titre="Résultat de la validation de votre inscription",
            message=f"Votre inscription a été {'acceptée' if body.approved else 'refusée'} par le médecin MH."
            + (f" {body.notes}" if body.notes else ""),
            lien_relation_id=user.id,
            lien_relation_type="user",
        )
    )
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user"""
    if current_user.id != user_id and current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    password_reset: UserPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reset a user's password (admin only)"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Validate password using service
    is_valid, error_message = UserService.validate_password(password_reset.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.hashed_password = get_password_hash(password_reset.new_password)
    db.commit()

    return {"message": "Password reset successfully"}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete user (admin only)"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return None


