from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.enums import Role, StatutWorkflowSinistre
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.sinistre import Sinistre
from app.models.alerte import Alerte
from app.models.hospital import Hospital
from app.models.souscription import Souscription
from app.schemas.sinistre import SinistreResponse, SinistreWorkflowStepResponse
from app.schemas.alerte import AlerteResponse
from pydantic import BaseModel
from app.services.sinistre_workflow_service import update_workflow_step
from app.api.v1.sos import notify_hospital_reception, get_latest_questionnaire


router = APIRouter()


def require_admin_or_sos_operator(current_user: User = Depends(get_current_user)) -> User:
    """Dependency pour vérifier que l'utilisateur est admin ou SOS operator"""
    if current_user.role not in [Role.ADMIN, Role.SOS_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin or SOS operator access required."
        )
    return current_user


class AssignHospitalRequest(BaseModel):
    hospital_id: int


class CloseSinistreRequest(BaseModel):
    notes: Optional[str] = None


@router.get("/alertes", response_model=List[AlerteResponse])
async def get_all_alertes(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_sos_operator)
):
    """Obtenir toutes les alertes (pour les admins et SOS operators)"""
    query = db.query(Alerte)
    
    if statut:
        query = query.filter(Alerte.statut == statut)
    
    alertes = query.order_by(Alerte.created_at.desc()).offset(skip).limit(limit).all()
    return alertes


@router.get("/sinistres", response_model=List[SinistreResponse])
async def get_all_sinistres(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_sos_operator)
):
    """Obtenir tous les sinistres"""
    query = db.query(Sinistre)
    
    if statut:
        query = query.filter(Sinistre.statut == statut)
    
    sinistres = query.order_by(Sinistre.created_at.desc()).offset(skip).limit(limit).all()
    return sinistres


@router.get("/sinistres/{sinistre_id}", response_model=SinistreResponse)
async def get_sinistre(
    sinistre_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_sos_operator)
):
    """Obtenir un sinistre par ID"""
    sinistre = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()
    
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé"
        )
    
    return sinistre


@router.put("/sinistres/{sinistre_id}/assign-hospital", response_model=SinistreResponse)
async def assign_hospital(
    sinistre_id: int,
    request: AssignHospitalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_sos_operator)
):
    """Attribuer un hôpital à un sinistre"""
    sinistre = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()
    
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé"
        )
    
    # Vérifier que l'hôpital existe
    hospital = db.query(Hospital).filter(Hospital.id == request.hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hôpital non trouvé"
        )
    
    sinistre.hospital_id = request.hospital_id
    db.commit()
    db.refresh(sinistre)
    
    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first()
    souscription = None
    assure = None
    if sinistre.souscription_id:
        souscription = db.query(Souscription).filter(Souscription.id == sinistre.souscription_id).first()
        if souscription:
            assure = db.query(User).filter(User.id == souscription.user_id).first()
    
    medical_questionnaire = get_latest_questionnaire(db, sinistre.souscription_id)
    if alerte:
        await notify_hospital_reception(
            db=db,
            sinistre=sinistre,
            alerte=alerte,
            hospital=hospital,
            souscription=souscription,
            assure=assure,
            medical_questionnaire=medical_questionnaire
        )
    
    return sinistre


@router.put("/sinistres/{sinistre_id}/close", response_model=SinistreResponse)
async def close_sinistre(
    sinistre_id: int,
    request: CloseSinistreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_sos_operator)
):
    """Clôturer un sinistre"""
    sinistre = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()
    
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé"
        )
    
    sinistre.statut = "resolu"
    if request.notes:
        existing_notes = sinistre.notes or ""
        new_notes = f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Clôture: {request.notes}\n{existing_notes}"
        sinistre.notes = new_notes
    
    # Mettre à jour aussi le statut de l'alerte associée
    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first()
    if alerte:
        alerte.statut = "resolue"
    
    db.commit()
    db.refresh(sinistre)
    
    return sinistre


class UpdateNotesRequest(BaseModel):
    notes: str


class UpdateWorkflowStepRequest(BaseModel):
    statut: StatutWorkflowSinistre
    notes: Optional[str] = None


@router.put("/sinistres/{sinistre_id}/update-notes", response_model=SinistreResponse)
async def update_sinistre_notes(
    sinistre_id: int,
    request: UpdateNotesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_sos_operator)
):
    """Mettre à jour les notes d'un sinistre"""
    sinistre = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()
    
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé"
        )
    
    existing_notes = sinistre.notes or ""
    new_notes = f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {current_user.email}: {request.notes}\n{existing_notes}"
    sinistre.notes = new_notes
    
    db.commit()
    db.refresh(sinistre)
    
    return sinistre


@router.put("/sinistres/{sinistre_id}/workflow/{step_key}", response_model=SinistreWorkflowStepResponse)
async def update_workflow_step_status(
    sinistre_id: int,
    step_key: str,
    request: UpdateWorkflowStepRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_sos_operator),
):
    """Mettre à jour le statut d'une étape du processus sinistre"""
    sinistre = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()

    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé"
        )

    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first()

    try:
        step = update_workflow_step(
            db,
            sinistre,
            alerte,
            step_key,
            request.statut,
            actor_id=current_user.id,
            notes=request.notes,
        )
        db.commit()
        db.refresh(step)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Étape {step_key} introuvable"
        )

    return step

