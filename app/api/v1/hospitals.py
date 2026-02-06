from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from app.core.database import get_db
from app.core.enums import Role
from app.core.security import get_password_hash
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.hospital import Hospital
from app.models.hospital_exam_tarif import HospitalExamTarif
from app.models.hospital_act_tarif import HospitalActTarif
from app.models.prestation import Prestation
from app.models.rapport import Rapport
from app.models.sinistre import Sinistre
from app.services.minio_service import MinioService
from app.schemas.hospital import (
    HospitalResponse,
    HospitalDetailResponse,
    HospitalCreate,
    HospitalUpdate,
    HospitalMapMarker,
    HospitalReceptionistCreate,
    HospitalUserSummary,
)
from app.schemas.hospital_exam_tarif import (
    HospitalExamTarifResponse,
    HospitalExamTarifCreate,
    HospitalExamTarifUpdate,
)
from app.schemas.hospital_act_tarif import (
    HospitalActTarifResponse,
    HospitalActTarifCreate,
    HospitalActTarifUpdate,
)
from app.schemas.hospital_medical_catalog import (
    HospitalMedicalCatalogResponse,
    HospitalMedicalCatalogDefaults,
)
from app.schemas.user import UserResponse
from pydantic import BaseModel, Field
import uuid
import logging

from app.core.constants import (
    HOSPITAL_STAY_DEFAULT_ACT_PRICE,
    HOSPITAL_STAY_DEFAULT_EXAM_PRICE,
    HOSPITAL_STAY_HOURLY_RATE,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user


def _get_hospital_or_404(db: Session, hospital_id: int) -> Hospital:
    hospital = (
        db.query(Hospital)
        .options(joinedload(Hospital.exam_tarifs))
        .filter(Hospital.id == hospital_id)
        .first()
    )
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found",
        )
    return hospital


def _ensure_exam_tarif_permission(current_user: User, hospital: Hospital):
    allowed_roles = {Role.ADMIN, Role.HOSPITAL_ADMIN, Role.AGENT_COMPTABLE_HOPITAL}
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to manage exam tarifs.",
        )
    if current_user.role == Role.ADMIN:
        return
    if current_user.hospital_id != hospital.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cet hôpital n'est pas associé à votre compte.",
        )


def _ensure_medecin_referent(db: Session, medecin_referent_id: Optional[int]) -> Optional[User]:
    if not medecin_referent_id:
        return None
    doctor = db.query(User).filter(User.id == medecin_referent_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Médecin référent introuvable"
        )
    if doctor.role not in {Role.MEDECIN_REFERENT_MH, Role.DOCTOR}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'utilisateur sélectionné n'est pas un médecin référent"
        )
    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le médecin référent sélectionné est inactif"
        )
    return doctor


def _assign_receptionists(db: Session, hospital: Hospital, receptionist_ids: Optional[List[int]]):
    if receptionist_ids is None:
        return
    ids_set = set(receptionist_ids)
    valid_users: List[User] = []
    if ids_set:
        valid_users = db.query(User).filter(User.id.in_(ids_set)).all()
        found_ids = {user.id for user in valid_users if user.role == Role.AGENT_RECEPTION_HOPITAL}
        invalid = ids_set - found_ids
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Réceptionniste(s) introuvable(s) ou avec un rôle invalide: {sorted(invalid)}"
            )
    # Détacher les réceptionnistes non souhaités
    current_receptionists = [
        user for user in hospital.receptionists
        if user.role == Role.AGENT_RECEPTION_HOPITAL
    ]
    for user in current_receptionists:
        if user.id not in ids_set:
            user.hospital_id = None
    # Assigner les nouveaux
    for user in valid_users:
        user.hospital_id = hospital.id


def _assign_doctors(db: Session, hospital: Hospital, doctor_ids: Optional[List[int]]):
    if doctor_ids is None:
        return
    ids_set = set(doctor_ids)
    # Uniquement les médecins hospitaliers (pas les médecins génériques ni les médecins référents MH)
    allowed_roles = {Role.MEDECIN_HOPITAL}
    valid_users: List[User] = []
    if ids_set:
        users = db.query(User).filter(User.id.in_(ids_set)).all()
        valid_users = [user for user in users if user.role in allowed_roles]
        found_ids = {user.id for user in valid_users}
        invalid = ids_set - found_ids
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Médecin(s) hospitalier(s) introuvable(s) ou avec un rôle invalide. Seuls les médecins hospitaliers (medecin_hopital) sont autorisés: {sorted(invalid)}"
            )

    current_doctors = db.query(User).filter(
        User.hospital_id == hospital.id,
        User.role == Role.MEDECIN_HOPITAL
    ).all()
    for doctor in current_doctors:
        if doctor.id not in ids_set:
            doctor.hospital_id = None
    for doctor in valid_users:
        doctor.hospital_id = hospital.id


def _assign_accountants(db: Session, hospital: Hospital, accountant_ids: Optional[List[int]]):
    if accountant_ids is None:
        return
    ids_set = set(accountant_ids)
    valid_users: List[User] = []
    if ids_set:
        users = db.query(User).filter(User.id.in_(ids_set)).all()
        valid_users = [user for user in users if user.role == Role.AGENT_COMPTABLE_HOPITAL]
        found_ids = {user.id for user in valid_users}
        invalid = ids_set - found_ids
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent(s) comptable(s) introuvable(s) ou avec un rôle invalide: {sorted(invalid)}"
            )

    current_accountants = db.query(User).filter(
        User.hospital_id == hospital.id,
        User.role == Role.AGENT_COMPTABLE_HOPITAL
    ).all()
    for accountant in current_accountants:
        if accountant.id not in ids_set:
            accountant.hospital_id = None
    for accountant in valid_users:
        accountant.hospital_id = hospital.id


class PrestationCreate(BaseModel):
    sinistre_id: Optional[int] = None
    user_id: Optional[int] = None
    code_prestation: str = Field(..., min_length=1, max_length=50)
    libelle: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    montant_unitaire: Decimal = Field(..., gt=0)
    quantite: int = Field(default=1, ge=1)
    date_prestation: datetime


class PrestationResponse(BaseModel):
    id: int
    hospital_id: int
    code_prestation: str
    libelle: str
    montant_unitaire: Decimal
    quantite: int
    montant_total: Decimal
    date_prestation: datetime
    statut: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[HospitalResponse])
async def list_hospitals(
    est_actif: Optional[bool] = None,
    ville: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la liste des hôpitaux pour les interfaces admin/back-office."""
    query = db.query(Hospital)
    
    if est_actif is not None:
        query = query.filter(Hospital.est_actif == est_actif)
    if ville:
        query = query.filter(Hospital.ville == ville)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Hospital.nom.ilike(pattern),
                Hospital.ville.ilike(pattern),
                Hospital.pays.ilike(pattern)
            )
        )
    
    hospitals = query.order_by(Hospital.nom.asc()).offset(skip).limit(limit).all()
    return hospitals


@router.get("/map/markers", response_model=List[HospitalMapMarker])
async def get_map_markers(
    only_active: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retourner les hôpitaux avec leurs coordonnées pour affichage sur carte."""
    query = db.query(Hospital)
    if only_active:
        query = query.filter(Hospital.est_actif == True)
    hospitals = query.all()
    return hospitals


@router.get("/{hospital_id}", response_model=HospitalResponse)
async def get_hospital_by_id(
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir un hôpital spécifique."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    return hospital


@router.get("/{hospital_id}/details", response_model=HospitalDetailResponse)
async def get_hospital_details(
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir les détails d'un hôpital, y compris les réceptionnistes."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    receptionists = [
        user for user in hospital.receptionists
        if user.role == Role.AGENT_RECEPTION_HOPITAL
    ]
    doctors = db.query(User).filter(
        User.hospital_id == hospital_id,
        User.role == Role.MEDECIN_HOPITAL
    ).order_by(User.full_name.asc().nullslast()).all()

    accountants = db.query(User).filter(
        User.hospital_id == hospital_id,
        User.role == Role.AGENT_COMPTABLE_HOPITAL
    ).order_by(User.full_name.asc().nullslast()).all()

    detail = HospitalDetailResponse.model_validate(hospital)
    detail.receptionists = [
        HospitalUserSummary.model_validate(user) for user in receptionists
    ]
    detail.receptionists_count = hospital.receptionists_count
    detail.doctors = [
        HospitalUserSummary.model_validate(user) for user in doctors
    ]
    detail.doctors_count = len(doctors)
    detail.accountants = [
        HospitalUserSummary.model_validate(user) for user in accountants
    ]
    detail.accountants_count = len(accountants)
    detail.exam_tarifs = [
        HospitalExamTarifResponse.model_validate(tarif) for tarif in hospital.exam_tarifs
    ]
    detail.act_tarifs = [
        HospitalActTarifResponse.model_validate(tarif) for tarif in hospital.act_tarifs
    ]
    return detail


@router.post("/", response_model=HospitalResponse, status_code=status.HTTP_201_CREATED)
async def create_hospital(
    hospital_data: HospitalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Créer un nouvel hôpital affilié à Mobility Health."""
    existing = db.query(Hospital).filter(
        Hospital.nom == hospital_data.nom,
        Hospital.ville == hospital_data.ville
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un hôpital avec ce nom existe déjà dans cette ville"
        )
    
    doctor = _ensure_medecin_referent(db, hospital_data.medecin_referent_id)
    payload = hospital_data.model_dump(exclude={"receptionist_ids", "doctor_ids", "accountant_ids"})
    hospital = Hospital(**payload)
    if doctor:
        hospital.medecin_referent_id = doctor.id
    
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    
    _assign_receptionists(db, hospital, hospital_data.receptionist_ids)
    _assign_doctors(db, hospital, hospital_data.doctor_ids)
    _assign_accountants(db, hospital, hospital_data.accountant_ids)
    db.commit()
    db.refresh(hospital)
    
    return hospital


@router.put("/{hospital_id}", response_model=HospitalResponse)
async def update_hospital(
    hospital_id: int,
    hospital_update: HospitalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Mettre à jour les informations d'un hôpital."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    
    update_data = hospital_update.model_dump(
        exclude_unset=True,
        exclude={"receptionist_ids", "doctor_ids", "accountant_ids"}
    )
    for field, value in update_data.items():
        setattr(hospital, field, value)
    
    if "medecin_referent_id" in hospital_update.model_dump(exclude_unset=True):
        doctor = _ensure_medecin_referent(db, hospital_update.medecin_referent_id)
        hospital.medecin_referent_id = doctor.id if doctor else None
    
    db.commit()
    db.refresh(hospital)
    
    _assign_receptionists(db, hospital, hospital_update.receptionist_ids)
    _assign_doctors(db, hospital, hospital_update.doctor_ids)
    _assign_accountants(db, hospital, hospital_update.accountant_ids)
    db.commit()
    db.refresh(hospital)
    return hospital


@router.get("/{hospital_id}/receptionists", response_model=List[UserResponse])
async def list_hospital_receptionists(
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Lister les réceptionnistes assignés à un hôpital."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    users = db.query(User).filter(
        User.hospital_id == hospital_id,
        User.role == Role.AGENT_RECEPTION_HOPITAL
    ).order_by(User.full_name.asc()).all()
    return users


@router.post("/{hospital_id}/receptionists", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_hospital_receptionist(
    hospital_id: int,
    receptionist_data: HospitalReceptionistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Créer un agent de réception rattaché à un hôpital."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    if not receptionist_data.password or len(receptionist_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    if db.query(User).filter(User.email == receptionist_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    if db.query(User).filter(User.username == receptionist_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    receptionist = User(
        email=receptionist_data.email,
        username=receptionist_data.username,
        hashed_password=get_password_hash(receptionist_data.password),
        full_name=receptionist_data.full_name,
        is_active=receptionist_data.is_active,
        role=Role.AGENT_RECEPTION_HOPITAL,
        hospital_id=hospital_id,
        is_superuser=False
    )
    
    db.add(receptionist)
    db.commit()
    db.refresh(receptionist)
    return receptionist


@router.get(
    "/{hospital_id}/exam-tarifs",
    response_model=List[HospitalExamTarifResponse],
)
async def list_hospital_exam_tarifs(
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hospital = (
        db.query(Hospital)
        .options(joinedload(Hospital.exam_tarifs))
        .filter(Hospital.id == hospital_id)
        .first()
    )
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    _ensure_exam_tarif_permission(current_user, hospital)
    return [
        HospitalExamTarifResponse.model_validate(tarif)
        for tarif in hospital.exam_tarifs
    ]


@router.post(
    "/{hospital_id}/exam-tarifs",
    response_model=HospitalExamTarifResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_hospital_exam_tarif(
    hospital_id: int,
    payload: HospitalExamTarifCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hospital = _get_hospital_or_404(db, hospital_id)
    _ensure_exam_tarif_permission(current_user, hospital)

    existing = (
        db.query(HospitalExamTarif)
        .filter(
            HospitalExamTarif.hospital_id == hospital_id,
            HospitalExamTarif.nom == payload.nom,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un examen avec ce nom existe déjà pour cet hôpital.",
        )

    tarif = HospitalExamTarif(
        hospital_id=hospital_id,
        nom=payload.nom,
        montant=payload.montant,
    )
    db.add(tarif)
    db.commit()
    db.refresh(tarif)
    return HospitalExamTarifResponse.model_validate(tarif)


@router.put(
    "/{hospital_id}/exam-tarifs/{tarif_id}",
    response_model=HospitalExamTarifResponse,
)
async def update_hospital_exam_tarif(
    hospital_id: int,
    tarif_id: int,
    payload: HospitalExamTarifUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hospital = _get_hospital_or_404(db, hospital_id)
    _ensure_exam_tarif_permission(current_user, hospital)

    tarif = (
        db.query(HospitalExamTarif)
        .filter(
            HospitalExamTarif.id == tarif_id,
            HospitalExamTarif.hospital_id == hospital_id,
        )
        .first()
    )
    if not tarif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarif introuvable")

    update_data = payload.model_dump(exclude_unset=True)
    if "nom" in update_data:
        duplicate = (
            db.query(HospitalExamTarif)
            .filter(
                HospitalExamTarif.hospital_id == hospital_id,
                HospitalExamTarif.nom == update_data["nom"],
                HospitalExamTarif.id != tarif_id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un examen avec ce nom existe déjà pour cet hôpital.",
            )

    for field, value in update_data.items():
        setattr(tarif, field, value)

    db.commit()
    db.refresh(tarif)
    return HospitalExamTarifResponse.model_validate(tarif)


@router.delete(
    "/{hospital_id}/exam-tarifs/{tarif_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_hospital_exam_tarif(
    hospital_id: int,
    tarif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hospital = _get_hospital_or_404(db, hospital_id)
    _ensure_exam_tarif_permission(current_user, hospital)

    tarif = (
        db.query(HospitalExamTarif)
        .filter(
            HospitalExamTarif.id == tarif_id,
            HospitalExamTarif.hospital_id == hospital_id,
        )
        .first()
    )
    if not tarif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarif introuvable")

    db.delete(tarif)
    db.commit()
    return None


@router.get(
    "/{hospital_id}/act-tarifs",
    response_model=List[HospitalActTarifResponse],
)
async def list_hospital_act_tarifs(
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hospital = (
        db.query(Hospital)
        .options(joinedload(Hospital.act_tarifs))
        .filter(Hospital.id == hospital_id)
        .first()
    )
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    _ensure_exam_tarif_permission(current_user, hospital)
    return [
        HospitalActTarifResponse.model_validate(tarif)
        for tarif in hospital.act_tarifs
    ]


@router.post(
    "/{hospital_id}/act-tarifs",
    response_model=HospitalActTarifResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_hospital_act_tarif(
    hospital_id: int,
    payload: HospitalActTarifCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hospital = _get_hospital_or_404(db, hospital_id)
    _ensure_exam_tarif_permission(current_user, hospital)

    duplicate_name = (
        db.query(HospitalActTarif)
        .filter(
            HospitalActTarif.hospital_id == hospital_id,
            HospitalActTarif.nom == payload.nom,
        )
        .first()
    )
    if duplicate_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un acte avec ce nom existe déjà pour cet hôpital.",
        )
    if payload.code:
        duplicate_code = (
            db.query(HospitalActTarif)
            .filter(
                HospitalActTarif.hospital_id == hospital_id,
                HospitalActTarif.code == payload.code,
            )
            .first()
        )
        if duplicate_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un acte avec ce code existe déjà pour cet hôpital.",
            )

    tarif = HospitalActTarif(
        hospital_id=hospital_id,
        nom=payload.nom,
        montant=payload.montant,
        code=payload.code,
        description=payload.description,
    )
    db.add(tarif)
    db.commit()
    db.refresh(tarif)
    return HospitalActTarifResponse.model_validate(tarif)


@router.put(
    "/{hospital_id}/act-tarifs/{tarif_id}",
    response_model=HospitalActTarifResponse,
)
async def update_hospital_act_tarif(
    hospital_id: int,
    tarif_id: int,
    payload: HospitalActTarifUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hospital = _get_hospital_or_404(db, hospital_id)
    _ensure_exam_tarif_permission(current_user, hospital)

    tarif = (
        db.query(HospitalActTarif)
        .filter(
            HospitalActTarif.id == tarif_id,
            HospitalActTarif.hospital_id == hospital_id,
        )
        .first()
    )
    if not tarif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarif introuvable")

    update_data = payload.model_dump(exclude_unset=True)
    if "nom" in update_data:
        duplicate = (
            db.query(HospitalActTarif)
            .filter(
                HospitalActTarif.hospital_id == hospital_id,
                HospitalActTarif.nom == update_data["nom"],
                HospitalActTarif.id != tarif_id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un acte avec ce nom existe déjà pour cet hôpital.",
            )
    if "code" in update_data and update_data["code"]:
        duplicate_code = (
            db.query(HospitalActTarif)
            .filter(
                HospitalActTarif.hospital_id == hospital_id,
                HospitalActTarif.code == update_data["code"],
                HospitalActTarif.id != tarif_id,
            )
            .first()
        )
        if duplicate_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un acte avec ce code existe déjà pour cet hôpital.",
            )

    for field, value in update_data.items():
        setattr(tarif, field, value)

    db.commit()
    db.refresh(tarif)
    return HospitalActTarifResponse.model_validate(tarif)


@router.delete(
    "/{hospital_id}/act-tarifs/{tarif_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_hospital_act_tarif(
    hospital_id: int,
    tarif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hospital = _get_hospital_or_404(db, hospital_id)
    _ensure_exam_tarif_permission(current_user, hospital)

    tarif = (
        db.query(HospitalActTarif)
        .filter(
            HospitalActTarif.id == tarif_id,
            HospitalActTarif.hospital_id == hospital_id,
        )
        .first()
    )
    if not tarif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarif introuvable")

    db.delete(tarif)
    db.commit()
    return None


@router.get(
    "/{hospital_id}/medical-catalog",
    response_model=HospitalMedicalCatalogResponse,
)
async def get_hospital_medical_catalog(
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hospital = (
        db.query(Hospital)
        .options(
            joinedload(Hospital.exam_tarifs),
            joinedload(Hospital.act_tarifs),
        )
        .filter(Hospital.id == hospital_id)
        .first()
    )
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    _ensure_exam_tarif_permission(current_user, hospital)
    return HospitalMedicalCatalogResponse(
        hospital_id=hospital.id,
        examens=[
            HospitalExamTarifResponse.model_validate(tarif)
            for tarif in hospital.exam_tarifs
        ],
        actes=[
            HospitalActTarifResponse.model_validate(tarif)
            for tarif in hospital.act_tarifs
        ],
        defaults=HospitalMedicalCatalogDefaults(
            hourly_rate=HOSPITAL_STAY_HOURLY_RATE,
            default_act_price=HOSPITAL_STAY_DEFAULT_ACT_PRICE,
            default_exam_price=HOSPITAL_STAY_DEFAULT_EXAM_PRICE,
        ),
    )


class RapportResponse(BaseModel):
    id: int
    hospital_id: int
    titre: str
    type_rapport: str
    fichier_nom: Optional[str]
    est_signe: bool
    statut: str
    created_at: datetime
    
    class Config:
        from_attributes = True


def require_hospital_role(current_user: User):
    """Vérifier que l'utilisateur a les droits hôpital"""
    if current_user.role not in [Role.HOSPITAL_ADMIN, Role.ADMIN, Role.DOCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Hospital admin, doctor or admin required."
        )


@router.post("/{hospital_id}/prestations/add", response_model=PrestationResponse, status_code=status.HTTP_201_CREATED)
async def add_prestation(
    hospital_id: int,
    prestation_data: PrestationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ajouter une prestation à un hôpital"""
    require_hospital_role(current_user)
    
    # Vérifier que l'hôpital existe
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    
    # Vérifier que l'hôpital est actif
    if not hospital.est_actif:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hospital is not active"
        )
    
    # Vérifier le sinistre si fourni
    if prestation_data.sinistre_id:
        sinistre = db.query(Sinistre).filter(Sinistre.id == prestation_data.sinistre_id).first()
        if not sinistre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sinistre not found"
            )
    
    # Calculer le montant total
    montant_total = prestation_data.montant_unitaire * prestation_data.quantite
    
    # Créer la prestation
    prestation = Prestation(
        hospital_id=hospital_id,
        sinistre_id=prestation_data.sinistre_id,
        user_id=prestation_data.user_id or current_user.id,
        code_prestation=prestation_data.code_prestation,
        libelle=prestation_data.libelle,
        description=prestation_data.description,
        montant_unitaire=prestation_data.montant_unitaire,
        quantite=prestation_data.quantite,
        montant_total=montant_total,
        date_prestation=prestation_data.date_prestation,
        statut="pending"
    )
    
    db.add(prestation)
    db.commit()
    db.refresh(prestation)
    
    logger.info(f"Prestation {prestation.id} added to hospital {hospital_id}")
    
    return PrestationResponse(
        id=prestation.id,
        hospital_id=prestation.hospital_id,
        code_prestation=prestation.code_prestation,
        libelle=prestation.libelle,
        montant_unitaire=prestation.montant_unitaire,
        quantite=prestation.quantite,
        montant_total=prestation.montant_total,
        date_prestation=prestation.date_prestation,
        statut=prestation.statut
    )


@router.post("/{hospital_id}/rapport", response_model=RapportResponse, status_code=status.HTTP_201_CREATED)
async def upload_rapport(
    hospital_id: int,
    titre: str = Form(...),
    type_rapport: str = Form(...),
    sinistre_id: Optional[int] = Form(None),
    user_id: Optional[int] = Form(None),
    est_signe: bool = Form(False),
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Uploader un rapport signé pour un hôpital"""
    require_hospital_role(current_user)
    
    # Vérifier que l'hôpital existe
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    
    # Vérifier le sinistre si fourni
    if sinistre_id:
        sinistre = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()
        if not sinistre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sinistre not found"
            )
    
    # Uploader le fichier vers Minio
    try:
        file_extension = fichier.filename.split('.')[-1] if '.' in fichier.filename else 'pdf'
        file_name = f"rapports/{hospital_id}/{uuid.uuid4()}.{file_extension}"
        
        # Lire le contenu du fichier
        file_content = await fichier.read()
        file_size = len(file_content)
        
        # Uploader vers Minio
        minio_service = MinioService()
        minio_service.upload_file(
            bucket_name="documents",
            object_name=file_name,
            file_data=file_content,
            content_type=fichier.content_type or "application/pdf"
        )
        
        # Créer le rapport
        rapport = Rapport(
            hospital_id=hospital_id,
            sinistre_id=sinistre_id,
            user_id=user_id or current_user.id,
            titre=titre,
            type_rapport=type_rapport,
            fichier_path=file_name,
            fichier_nom=fichier.filename,
            fichier_taille=file_size,
            fichier_type=fichier.content_type or "application/pdf",
            est_signe=est_signe,
            signe_par=current_user.id if est_signe else None,
            date_signature=datetime.utcnow() if est_signe else None,
            statut="signed" if est_signe else "draft"
        )
        
        db.add(rapport)
        db.commit()
        db.refresh(rapport)
        
        logger.info(f"Rapport {rapport.id} uploaded for hospital {hospital_id}")
        
        return RapportResponse(
            id=rapport.id,
            hospital_id=rapport.hospital_id,
            titre=rapport.titre,
            type_rapport=rapport.type_rapport,
            fichier_nom=rapport.fichier_nom,
            est_signe=rapport.est_signe,
            statut=rapport.statut,
            created_at=rapport.created_at
        )
        
    except Exception as e:
        logger.error(f"Error uploading rapport: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/{hospital_id}/prestations", response_model=List[PrestationResponse])
async def get_prestations(
    hospital_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la liste des prestations d'un hôpital"""
    require_hospital_role(current_user)
    
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    
    prestations = db.query(Prestation).filter(
        Prestation.hospital_id == hospital_id
    ).offset(skip).limit(limit).all()
    
    return [
        PrestationResponse(
            id=p.id,
            hospital_id=p.hospital_id,
            code_prestation=p.code_prestation,
            libelle=p.libelle,
            montant_unitaire=p.montant_unitaire,
            quantite=p.quantite,
            montant_total=p.montant_total,
            date_prestation=p.date_prestation,
            statut=p.statut
        )
        for p in prestations
    ]
