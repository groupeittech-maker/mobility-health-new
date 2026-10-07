import json
import logging
import random
import string
from typing import List, Union, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from app.core.database import get_db
from app.core.enums import Role
from app.core.permissions import (
    F_COMPTES_ASSUREURS,
    F_COMPTES_INTERMEDIAIRES,
    F_COMPTES_MEDECINS_CONSEIL,
    F_COMPTES_PARTENAIRES_SANTE,
    F_COMPTES_REASSUREURS,
    F_COMPTES_UTILISATEURS,
    LEVEL_EDITION,
    has_permission,
    is_internal_backoffice_role,
)
from app.core.redis_client import get_redis
from app.core.security import get_password_hash
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.services.email_delivery import dispatch_email, EmailDeliveryError
from app.services.user_service import UserService
from app.models.attestation import Attestation
from app.models.souscription import Souscription
from app.schemas.attestation import AttestationResponse
from pydantic import BaseModel, EmailStr, field_serializer

logger = logging.getLogger(__name__)

router = APIRouter()


# Rôle cible du compte → fonctionnalité « Gestion des comptes » exigée chez le
# créateur (niveau Édition). Correspond aux lignes « Création de compte … » de
# la matrice : la création reste centralisée côté MHC — superviseur technique
# pour assureur/réassureur/intermédiaire, superviseur affaires médicales pour
# médecin-conseil/partenaire santé, super admin pour tout.
_CREATION_COMPTE_FEATURE = {
    Role.MEDECIN_REFERENT_MH: F_COMPTES_MEDECINS_CONSEIL,
    Role.DOCTOR: F_COMPTES_MEDECINS_CONSEIL,
    Role.MEDECIN_HOPITAL: F_COMPTES_PARTENAIRES_SANTE,
    Role.AGENT_RECEPTION_HOPITAL: F_COMPTES_PARTENAIRES_SANTE,
    Role.AGENT_COMPTABLE_HOPITAL: F_COMPTES_PARTENAIRES_SANTE,
    Role.HOSPITAL_ADMIN: F_COMPTES_PARTENAIRES_SANTE,
    Role.AGENT_PRODUCTION_ASSUREUR: F_COMPTES_ASSUREURS,
    Role.AGENT_SINISTRE_ASSUREUR: F_COMPTES_ASSUREURS,
    Role.AGENT_COMPTABLE_ASSUREUR: F_COMPTES_ASSUREURS,
    Role.AGENT_MEDICAL_ASSUREUR: F_COMPTES_ASSUREURS,
    Role.AGENT_PRODUCTION_COURTIER: F_COMPTES_INTERMEDIAIRES,
    Role.AGENT_SINISTRE_COURTIER: F_COMPTES_INTERMEDIAIRES,
    Role.AGENT_COMPTABLE_COURTIER: F_COMPTES_INTERMEDIAIRES,
    Role.ASSISTANT_SOUSCRIPTION: F_COMPTES_INTERMEDIAIRES,
    Role.AGENT_VERIFICATEUR_REASSUREUR: F_COMPTES_REASSUREURS,
}


def _role_value(role) -> str:
    if hasattr(role, "value"):
        role = role.value
    return str(role or "user").lower()


def _feature_gestion_compte(role_value: str) -> str:
    try:
        role_enum = Role(role_value)
    except ValueError:
        return F_COMPTES_UTILISATEURS
    return _CREATION_COMPTE_FEATURE.get(role_enum, F_COMPTES_UTILISATEURS)


def _can_manage_account(actor: User, target_role_value: str) -> bool:
    """L'acteur peut-il gérer un compte du rôle `target_role_value` ?
    Admin : tout. Sinon : niveau Édition sur la fonctionnalité « Gestion des
    comptes » correspondant au rôle cible (matrice MHC)."""
    actor_role = _role_value(getattr(actor, "role", None))
    if actor_role == "admin":
        return True
    return has_permission(actor_role, _feature_gestion_compte(target_role_value), LEVEL_EDITION)


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
    reassureur_id: int | None = None


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    pays_residence: str | None = None
    is_active: bool | None = None
    role: Role | None = None
    hospital_id: int | None = None
    reassureur_id: int | None = None
    # Coordonnées modifiables depuis MyMHC (téléphone / contact d'urgence)
    telephone: str | None = None
    numero_whatsapp: str | None = None
    nom_contact_urgence: str | None = None
    contact_urgence: str | None = None
    date_naissance: str | None = None
    nationalite: str | None = None
    numero_passeport: str | None = None
    validite_passeport: str | None = None


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
    numero_whatsapp: str | None = None
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
    role: Optional[Union[Role, str]] = None,
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
    role_str = getattr(current_user, "role", None)
    if hasattr(role_str, "value"):
        role_str = role_str.value
    role_str = str(role_str or "").lower()
    is_admin = role_str == "admin"
    is_medical_reviewer = role_str in ("medical_reviewer", "medecin_referent_mh")
    if not is_admin and not is_internal_backoffice_role(role_str):
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
        role_val = role.value if hasattr(role, "value") else str(role)
        query = query.filter(text("LOWER(CAST(users.role AS TEXT)) = LOWER(:role_val)").bindparams(role_val=role_val))
    if validation_inscription:
        query = query.filter(User.validation_inscription == validation_inscription)
        if validation_inscription == "pending":
            query = query.filter(User.email_verified == True)
            query = query.filter(text("LOWER(CAST(users.role AS TEXT)) = 'user'"))
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
    Créer un nouvel utilisateur — création centralisée MHC : admin, ou profil
    interne avec le niveau Édition sur la fonctionnalité « Gestion des comptes »
    correspondant au rôle cible (matrice).
    
    Utilise le service UserService pour une validation complète et l'envoi d'email de bienvenue.
    """
    target_role = _role_value(getattr(user_data.role, "value", user_data.role))
    if not _can_manage_account(current_user, target_role):
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
        reassureur_id=user_data.reassureur_id,
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
    """Rechercher un utilisateur par nom d'utilisateur (profils MHC internes)"""
    if not is_internal_backoffice_role(_role_value(getattr(current_user, "role", None))):
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
    current_role = _role_value(getattr(current_user, "role", None))
    is_admin = current_role == "admin"
    is_medical_reviewer = current_role == "medical_reviewer"
    is_internal = is_internal_backoffice_role(current_role)
    if current_user.id != user_id and not is_admin and not is_internal:
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
    Si approuvée : un email d'activation finale est envoyé à l'utilisateur.
    """
    is_admin = current_user.role == Role.ADMIN
    is_medical_reviewer = _role_value(getattr(current_user, "role", None)) in ("medical_reviewer", "medecin_referent_mh")
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
        user.is_active = False
    else:
        user.is_active = False
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
    if body.approved:
        UserService.send_inscription_approval_email(user)
    else:
        UserService.send_inscription_rejection_email(user, body.notes)
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Changement des coordonnées avec vérification (kit MyMHC — Mon profil)
# ---------------------------------------------------------------------------

_CONTACT_CHANGE_CHANNELS = ("email", "sms", "whatsapp")


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    channel: str | None = "email"


class ChangePhoneRequest(BaseModel):
    new_phone: str
    channel: str | None = "sms"  # sms | whatsapp | email


class ContactChangeConfirm(BaseModel):
    code: str


def _issue_contact_change_code(user_id: int, kind: str, value: str) -> str:
    """Stocke {kind, value, code} dans Redis (15 min) et retourne le code."""
    redis = get_redis()
    if redis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service de vérification temporairement indisponible.",
        )
    code = "".join(random.choices(string.digits, k=6))
    redis.setex(
        f"contact_change:{user_id}",
        900,
        json.dumps({"kind": kind, "value": value, "code": code}),
    )
    return code


def _deliver_contact_change_code(
    channel: str,
    *,
    user: User,
    code: str,
    email: str | None = None,
    phone: str | None = None,
) -> None:
    """Envoie le code sur le canal demandé."""
    channel = (channel or "email").strip().lower()
    if channel not in _CONTACT_CHANGE_CHANNELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Canal de vérification inconnu : {channel}",
        )
    if channel == "email":
        to_email = email or user.email
        subject = "Code de vérification - Mobility Health"
        body_text = (
            f"Votre code de vérification MyMHC est : {code}\n"
            "Il est valable 15 minutes."
        )
        dispatch_email(
            to_email=to_email,
            subject=subject,
            body_html=(
                f"<p>Bonjour {user.full_name or user.username},</p>"
                f"<p>Votre code de vérification MyMHC est :</p>"
                f"<p style='font-size:28px;font-weight:bold;letter-spacing:6px;'>{code}</p>"
                "<p>Il est valable 15 minutes. Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.</p>"
            ),
            body_text=body_text,
            user_id=user.id,
            synchronous=True,
        )
        return
    destination = phone or user.numero_whatsapp or user.telephone
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun numéro de téléphone disponible pour ce canal.",
        )
    from app.integrations.messaging import get_messaging_client
    from app.integrations.messaging.schemas import MessageSendRequest

    get_messaging_client().send(
        MessageSendRequest(
            channel=channel,
            to=destination,
            message=f"MyMHC : votre code de vérification est {code} (valide 15 min).",
            reference=f"contact_change:{user.id}",
        )
    )


def _consume_contact_change_code(user_id: int, kind: str, code: str) -> str:
    """Vérifie le code et retourne la valeur en attente ; lève 400 sinon."""
    redis = get_redis()
    if redis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service de vérification temporairement indisponible.",
        )
    raw = redis.get(f"contact_change:{user_id}")
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun code en attente. Recommencez la demande.",
        )
    data = json.loads(raw)
    if data.get("kind") != kind or data.get("code") != code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code de vérification incorrect.",
        )
    redis.delete(f"contact_change:{user_id}")
    return data["value"]


@router.post("/me/change-email/request")
async def request_change_email(
    body: ChangeEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Demande de changement d'adresse e-mail : code envoyé à la NOUVELLE adresse
    (ou par SMS/WhatsApp si demandé)."""
    new_email = str(body.new_email).strip().lower()
    if new_email == current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse e-mail est déjà la vôtre.",
        )
    existing = db.query(User).filter(
        or_(User.email == new_email, User.username == new_email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse e-mail est déjà utilisée.",
        )
    code = _issue_contact_change_code(current_user.id, "email", new_email)
    db_user = db.query(User).filter(User.id == current_user.id).first()
    _deliver_contact_change_code(
        body.channel or "email",
        user=db_user,
        code=code,
        email=new_email,
    )
    return {"message": "Code de vérification envoyé", "channel": body.channel or "email"}


@router.post("/me/change-email/confirm", response_model=UserResponse)
async def confirm_change_email(
    body: ContactChangeConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Applique le changement d'e-mail après vérification du code."""
    new_email = _consume_contact_change_code(current_user.id, "email", body.code)
    existing = db.query(User).filter(
        User.id != current_user.id,
        or_(User.email == new_email, User.username == new_email),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse e-mail est déjà utilisée.",
        )
    user = db.query(User).filter(User.id == current_user.id).first()
    user.email = new_email
    # L'identifiant de connexion est l'adresse e-mail pour les comptes auto-inscrits
    if user.username == current_user.email:
        user.username = new_email
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/change-phone/request")
async def request_change_phone(
    body: ChangePhoneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Demande de changement de numéro : code envoyé sur le nouveau numéro
    (SMS/WhatsApp) ou par e-mail."""
    new_phone = body.new_phone.strip()
    if len(new_phone) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Numéro de téléphone invalide.",
        )
    code = _issue_contact_change_code(current_user.id, "phone", new_phone)
    db_user = db.query(User).filter(User.id == current_user.id).first()
    channel = (body.channel or "sms").strip().lower()
    _deliver_contact_change_code(
        channel,
        user=db_user,
        code=code,
        phone=new_phone if channel in ("sms", "whatsapp") else None,
    )
    return {"message": "Code de vérification envoyé", "channel": channel}


@router.post("/me/change-phone/confirm", response_model=UserResponse)
async def confirm_change_phone(
    body: ContactChangeConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Applique le changement de numéro après vérification du code."""
    new_phone = _consume_contact_change_code(current_user.id, "phone", body.code)
    user = db.query(User).filter(User.id == current_user.id).first()
    user.telephone = new_phone
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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if current_user.id != user_id:
        target_role = _role_value(getattr(user, "role", None))
        new_role = _role_value(getattr(user_update.role, "value", user_update.role)) if getattr(user_update, "role", None) is not None else target_role
        if not (_can_manage_account(current_user, target_role) and _can_manage_account(current_user, new_role)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field in ("date_naissance", "validite_passeport"):
            # Colonnes Date : accepter le format ISO YYYY-MM-DD envoyé par l'app
            if value is None or value == "":
                setattr(user, field, None)
                continue
            try:
                value = datetime.strptime(str(value), "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Format de {field} invalide. Utilisez YYYY-MM-DD",
                )
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
    """Reset a user's password (créateur MHC habilité sur le rôle cible)"""
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
    if not _can_manage_account(current_user, _role_value(getattr(user, "role", None))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
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
    """
    Suppression définitive (admin uniquement) : alertes SOS, sinistres, séjours, factures,
    rapports, prestations, audit, souscriptions, attestations, questionnaires, paiements,
    projets, notifications, comptes financiers personnels, etc.
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer son propre compte"
        )

    UserService.delete_user_cascade(db, user_id=user_id, acting_user_id=current_user.id)
    return None


