from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, aliased

from app.api.v1.auth import get_current_user
from app.core.constants import (
    HOSPITAL_STAY_ACTS,
    HOSPITAL_STAY_EXAMS,
    HOSPITAL_STAY_ACT_PRICES,
    HOSPITAL_STAY_EXAM_PRICES,
    HOSPITAL_STAY_HOURLY_RATE,
    HOSPITAL_STAY_DEFAULT_ACT_PRICE,
    HOSPITAL_STAY_DEFAULT_EXAM_PRICE,
)
from app.core.database import get_db
from app.core.enums import Role, StatutWorkflowSinistre
from pydantic import BaseModel
from app.models.alerte import Alerte
from app.models.hospital import Hospital
from app.models.hospital_stay import HospitalStay
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.services.invoice_history import record_invoice_history
from app.models.notification import Notification
from app.models.sinistre import Sinistre
from app.models.sinistre_process_step import SinistreProcessStep
from app.models.user import User
from app.api.v1.sos import manager as websocket_manager
from app.schemas.hospital_stay import (
    HospitalStayCreate,
    HospitalStayResponse,
    HospitalStayReportUpdate,
    HospitalStayOptionsResponse,
    HospitalStayDoctorSummary,
    HospitalStayValidationRequest,
    HospitalStayInvoiceRequest,
)
from app.schemas.sinistre import SinistreResponse, SinistreWorkflowStepResponse
from app.services.sinistre_workflow_service import update_workflow_step
from app.services.referent_notification_reads import mark_notifications_read_for_relation

router = APIRouter()


class DispatchAmbulanceRequest(BaseModel):
    statut: StatutWorkflowSinistre = StatutWorkflowSinistre.COMPLETED
    notes: Optional[str] = None


def _get_sinistre_or_404(db: Session, sinistre_id: int) -> Sinistre:
    sinistre = (
        db.query(Sinistre)
        .options(joinedload(Sinistre.hospital))
        .filter(Sinistre.id == sinistre_id)
        .first()
    )
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre introuvable"
        )
    return sinistre


def _role_value(user: User) -> str:
    """Valeur du rôle en chaîne (insensible à enum vs string en base)."""
    r = getattr(user, "role", None)
    if r is None:
        return ""
    return r.value if hasattr(r, "value") else str(r).lower()


def _require_hospital_actor(user: User, sinistre: Sinistre, required_roles: set):
    role_val = _role_value(user)
    allowed = {r.value if hasattr(r, "value") else str(r).lower() for r in required_roles}
    if role_val not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
    if not sinistre.hospital_id or (user.hospital_id and user.hospital_id != sinistre.hospital_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cet hôpital n'est pas associé à votre compte")


def _user_is_referent_for_hospital(user: User, hospital: Optional[Hospital], sinistre: Sinistre) -> bool:
    if _role_value(user) != Role.MEDECIN_REFERENT_MH.value:
        return False
    if hospital and hospital.medecin_referent_id == user.id:
        return True
    if hospital and user.hospital_id == hospital.id:
        return True
    if sinistre.medecin_referent_id and sinistre.medecin_referent_id == user.id:
        return True
    return False


def _user_can_view_sinistre(user: User, sinistre: Sinistre) -> bool:
    unrestricted_roles = {
        Role.ADMIN,
        Role.SOS_OPERATOR,
        Role.AGENT_SINISTRE_MH,
        Role.DOCTOR,
    }
    role_val = _role_value(user)
    unrestricted_vals = {r.value for r in unrestricted_roles}
    if role_val in unrestricted_vals:
        return True

    hospital_roles = {
        Role.HOSPITAL_ADMIN,
        Role.AGENT_RECEPTION_HOPITAL,
        Role.AGENT_COMPTABLE_HOPITAL,
        Role.MEDECIN_HOPITAL,
    }
    hospital_vals = {r.value for r in hospital_roles}

    if sinistre.hospital_id:
        hospital = sinistre.hospital
        if role_val in hospital_vals and user.hospital_id == sinistre.hospital_id:
            return True
        if _user_is_referent_for_hospital(user, hospital, sinistre):
            return True

    return False


def _get_active_users_by_roles(
    db: Session,
    roles: set[Role],
    hospital_id: Optional[int] = None,
) -> List[User]:
    query = (
        db.query(User)
        .filter(
            User.role.in_(list(roles)),
            User.is_active == True,  # noqa: E712
        )
    )
    if hospital_id is not None:
        query = query.filter(User.hospital_id == hospital_id)
    return query.all()


def _get_users_by_role(db: Session, role: Role, hospital_id: int) -> List[User]:
    return _get_active_users_by_roles(db, {role}, hospital_id)


def _notify_users(
    db: Session,
    users: List[User],
    titre: str,
    message: str,
    relation_type: Optional[str],
    relation_id: Optional[int],
    type_notification: str = "hospital_stay",
    send_push_channel: bool = False,
):
    for user in users:
        notification = Notification(
            user_id=user.id,
            type_notification=type_notification,
            titre=titre,
            message=message,
            lien_relation_type=relation_type,
            lien_relation_id=relation_id,
        )
        db.add(notification)
        if send_push_channel:
            db.flush()
            try:
                from app.workers.tasks import send_notification_multi_channel

                send_notification_multi_channel.delay(
                    user_id=user.id,
                    notification_id=notification.id,
                    channels=["push"],
                )
            except Exception:
                pass


def _get_medical_referents_for_sinistre(db: Session, sinistre: Sinistre) -> List[User]:
    """Retourner les médecins référents à notifier pour un sinistre donné."""
    user_ids: set[int] = set()
    if sinistre.medecin_referent_id:
        user_ids.add(sinistre.medecin_referent_id)
    hospital = sinistre.hospital
    if hospital and hospital.medecin_referent_id:
        user_ids.add(hospital.medecin_referent_id)

    if not user_ids:
        # Fallback: notifier tous les médecins référents actifs
        return (
            db.query(User)
            .filter(
                User.role == Role.MEDECIN_REFERENT_MH,
                User.is_active == True,  # noqa: E712
            )
            .all()
        )

    return (
        db.query(User)
        .filter(
            User.id.in_(list(user_ids)),
            User.is_active == True,  # noqa: E712
        )
        .all()
    )


def _dispatch_referent_push_queue(push_queue: List[Tuple[int, int]]) -> None:
    """Après commit : le worker Celery doit voir les lignes `notifications`."""
    if not push_queue:
        return
    try:
        from app.workers.tasks import send_notification_multi_channel
    except Exception:
        return
    for user_id, notification_id in push_queue:
        try:
            send_notification_multi_channel.delay(
                user_id=user_id,
                notification_id=notification_id,
                channels=["push"],
            )
        except Exception:
            pass


async def _notify_medical_referents(
    db: Session,
    sinistre: Sinistre,
    titre: str,
    message: str,
    type_notification: str,
    push_queue: Optional[List[Tuple[int, int]]] = None,
):
    """
    Notifier les médecins référents MH d'un événement lié à un sinistre.
    Crée une notification en base, WebSocket immédiat ; push FCM après commit (push_queue).
    """
    recipients = _get_medical_referents_for_sinistre(db, sinistre)
    if not recipients:
        return
    
    # Récupérer l'alerte associée pour enrichir les notifications WebSocket
    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first() if sinistre.alerte_id else None
    
    for user in recipients:
        notification = Notification(
            user_id=user.id,
            type_notification=type_notification,
            titre=titre,
            message=message,
            lien_relation_type="sinistre",
            lien_relation_id=sinistre.id,
        )
        db.add(notification)
        db.flush()  # Pour obtenir l'ID de la notification

        if push_queue is not None:
            push_queue.append((user.id, notification.id))
        
        # Envoyer via WebSocket
        try:
            websocket_payload = {
                "type": "medical_notification",
                "notification_type": type_notification,
                "sinistre_id": sinistre.id,
                "titre": titre,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
            if alerte:
                websocket_payload.update({
                    "alerte_id": alerte.id,
                    "numero_alerte": alerte.numero_alerte,
                    "priorite": alerte.priorite,
                })
            await websocket_manager.send_personal_message(websocket_payload, user.id)
        except Exception:
            # Si WebSocket n'est pas disponible, on continue
            pass


def _resolve_hospital_ids_for_user(
    db: Session,
    user: User,
    requested_hospital_id: Optional[int] = None,
) -> List[int]:
    """Retourner les identifiants d'hôpitaux accessibles pour l'utilisateur."""
    hospital_roles = {
        Role.HOSPITAL_ADMIN,
        Role.AGENT_RECEPTION_HOPITAL,
        Role.AGENT_COMPTABLE_HOPITAL,
        Role.MEDECIN_HOPITAL,
    }
    role_val = _role_value(user)
    hospital_vals = {r.value for r in hospital_roles}

    if role_val in hospital_vals:
        if not user.hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucun hôpital n'est associé à votre compte.",
            )
        if requested_hospital_id and requested_hospital_id != user.hospital_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez pas accéder à cet hôpital.",
            )
        return [user.hospital_id]

    if role_val == Role.MEDECIN_REFERENT_MH.value:
        hospital_ids: List[int] = []
        if user.hospital_id:
            hospital_ids.append(user.hospital_id)
        referent_rows = (
            db.query(Hospital.id)
            .filter(Hospital.medecin_referent_id == user.id)
            .all()
        )
        hospital_ids.extend([row[0] for row in referent_rows])
        hospital_ids = list({hid for hid in hospital_ids if hid})
        if requested_hospital_id:
            if requested_hospital_id not in hospital_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Vous ne pouvez pas accéder à cet hôpital.",
                )
            return [requested_hospital_id]
        if not hospital_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Aucun hôpital accessible pour votre compte.",
            )
        return hospital_ids

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès réservé aux acteurs hospitaliers.",
    )


def _prepare_invoice_lines(stay: HospitalStay) -> List[dict]:
    lines: List[dict] = []
    hours = stay.report_duree_sejour_heures or 0
    if hours:
        qty = Decimal(str(hours))
        amount = HOSPITAL_STAY_HOURLY_RATE * qty
        lines.append(
            {
                "libelle": f"Durée de séjour ({hours}h)",
                "quantite": hours,
                "prix_unitaire": HOSPITAL_STAY_HOURLY_RATE,
                "montant_ht": amount,
            }
        )

    exam_tarifs_map = {}
    if getattr(stay, "hospital", None) and getattr(stay.hospital, "exam_tarifs", None):
        exam_tarifs_map = {tarif.nom: tarif.montant for tarif in stay.hospital.exam_tarifs}
    act_tarifs_map = {}
    if getattr(stay, "hospital", None) and getattr(stay.hospital, "act_tarifs", None):
        act_tarifs_map = {tarif.nom: tarif.montant for tarif in stay.hospital.act_tarifs}

    for act in stay.report_actes or []:
        price = act_tarifs_map.get(act, HOSPITAL_STAY_ACT_PRICES.get(act, HOSPITAL_STAY_DEFAULT_ACT_PRICE))
        lines.append(
            {
                "libelle": f"Acte - {act}",
                "quantite": 1,
                "prix_unitaire": price,
                "montant_ht": price,
            }
        )

    for exam in stay.report_examens or []:
        price = exam_tarifs_map.get(exam, HOSPITAL_STAY_EXAM_PRICES.get(exam, HOSPITAL_STAY_DEFAULT_EXAM_PRICE))
        lines.append(
            {
                "libelle": f"Examen - {exam}",
                "quantite": 1,
                "prix_unitaire": price,
                "montant_ht": price,
            }
        )
    return lines


def _can_access_hospital(user: User, hospital: Hospital) -> bool:
    rv = _role_value(user)
    if rv in (Role.HOSPITAL_ADMIN.value, Role.AGENT_RECEPTION_HOPITAL.value):
        return user.hospital_id == hospital.id
    if rv == Role.MEDECIN_REFERENT_MH.value:
        return (
            hospital.medecin_referent_id == user.id
            or user.hospital_id == hospital.id
        )
    return False


@router.get(
    "/sinistres/{sinistre_id}",
    response_model=SinistreResponse,
)
async def get_sinistre_summary(
    sinistre_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourner les informations principales d'un sinistre."""
    sinistre = _get_sinistre_or_404(db, sinistre_id)
    if not _user_can_view_sinistre(current_user, sinistre):
        detail = "Accès refusé"
        role_val = _role_value(current_user)
        hospital_vals = {r.value for r in (Role.HOSPITAL_ADMIN, Role.AGENT_RECEPTION_HOPITAL, Role.AGENT_COMPTABLE_HOPITAL, Role.MEDECIN_HOPITAL)}
        if role_val in hospital_vals:
            if not current_user.hospital_id:
                detail = "Accès refusé : aucun hôpital n'est associé à votre compte."
            elif sinistre.hospital_id and current_user.hospital_id != sinistre.hospital_id:
                detail = "Accès refusé : ce sinistre est rattaché à un autre hôpital."
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )
    return sinistre


@router.post(
    "/sinistres/{sinistre_id}/dispatch-ambulance",
    response_model=SinistreWorkflowStepResponse,
    status_code=status.HTTP_200_OK,
)
async def dispatch_ambulance(
    sinistre_id: int,
    request: DispatchAmbulanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sinistre = _get_sinistre_or_404(db, sinistre_id)
    if not sinistre.hospital_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun hôpital n'est associé à ce sinistre")

    _require_hospital_actor(
        current_user,
        sinistre,
        {Role.HOSPITAL_ADMIN, Role.AGENT_RECEPTION_HOPITAL},
    )

    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first()
    step = update_workflow_step(
        db,
        sinistre,
        alerte,
        "ambulance_en_route",
        request.statut,
        actor_id=current_user.id,
        notes=request.notes,
    )
    db.commit()
    db.refresh(step)
    return SinistreWorkflowStepResponse.model_validate(step)


@router.post(
    "/sinistres/{sinistre_id}/stays",
    response_model=HospitalStayResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_hospital_stay(
    sinistre_id: int,
    request: HospitalStayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sinistre = _get_sinistre_or_404(db, sinistre_id)
    if not sinistre.hospital_id or not sinistre.numero_sinistre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La prise en charge n'a pas encore été validée.",
        )
    if sinistre.hospital_stay:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un séjour existe déjà pour ce sinistre.")

    _require_hospital_actor(
        current_user,
        sinistre,
        {Role.HOSPITAL_ADMIN, Role.AGENT_RECEPTION_HOPITAL},
    )

    doctor = db.query(User).filter(User.id == request.doctor_id).first()
    if not doctor or doctor.hospital_id != sinistre.hospital_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médecin introuvable pour cet hôpital.")

    hospital = sinistre.hospital
    patient_id = sinistre.alerte.user_id if sinistre.alerte else None

    stay = HospitalStay(
        sinistre_id=sinistre.id,
        hospital_id=sinistre.hospital_id,
        patient_id=patient_id,
        assigned_doctor_id=doctor.id,
        created_by_id=current_user.id,
        orientation_notes=request.orientation_notes,
        service_concerne=request.service_concerne,
        chambre=request.chambre,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db.add(stay)

    # Marquer l'étape "medecin_en_route" comme en cours
    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first()
    update_workflow_step(
        db,
        sinistre,
        alerte,
        "medecin_en_route",
        StatutWorkflowSinistre.IN_PROGRESS,
        actor_id=current_user.id,
        notes="Orientation vers un médecin",
    )

    # Ne pas marquer l'alerte comme "resolue" ici : le dossier doit rester en cours
    # et apparaître dans "Sinistre à valider" pour le médecin référent. L'alerte
    # ne passera en "resolue" qu'à la validation compta de la facture (invoices.py)
    # ou à la clôture manuelle par l'admin (admin_sinistres.py).

    db.commit()
    db.refresh(stay)
    return HospitalStayResponse.model_validate(stay)


@router.put(
    "/hospital-stays/{stay_id}/report",
    response_model=HospitalStayResponse,
)
async def update_hospital_stay_report(
    stay_id: int,
    report: HospitalStayReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stay = (
        db.query(HospitalStay)
        .options(
            joinedload(HospitalStay.hospital)
            .joinedload(Hospital.exam_tarifs),
            joinedload(HospitalStay.hospital)
            .joinedload(Hospital.act_tarifs),
        )
        .filter(HospitalStay.id == stay_id)
        .first()
    )
    if not stay:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Séjour introuvable")

    sinistre = stay.sinistre
    is_assigned_doctor = stay.assigned_doctor_id == current_user.id

    if not is_assigned_doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le médecin hospitalier assigné peut compléter ce rapport."
        )
    if stay.status in {"validated", "invoiced"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le rapport a déjà été validé et ne peut plus être modifié.",
        )

    stay.report_motif_consultation = report.motif_consultation
    stay.report_motif_hospitalisation = report.motif_hospitalisation
    stay.report_duree_sejour_heures = report.duree_sejour_heures
    stay.report_actes = report.actes_effectues or []
    stay.report_examens = report.examens_effectues or []
    stay.report_resume = report.resume
    stay.report_observations = report.observations
    stay.report_submitted_at = datetime.utcnow()
    stay.report_submitted_by = current_user.id

    previous_report_status = stay.report_status
    # Dès que le médecin hospitalier enregistre le rapport, le dossier passe en "Rapport à valider" pour le médecin référent
    stay.report_status = "submitted"
    stay.status = "awaiting_validation"
    stay.validated_by_id = None
    stay.validated_at = None
    stay.validation_notes = None
    stay.ended_at = datetime.utcnow() if report.terminer_sejour else None

    referent_push_queue: List[Tuple[int, int]] = []
    should_notify_report = previous_report_status != "submitted" and stay.report_status == "submitted"
    if should_notify_report:
        if stay.assigned_doctor:
            doctor_name = (
                stay.assigned_doctor.full_name
                or stay.assigned_doctor.email
                or "le médecin assigné"
            )
        else:
            doctor_name = "le médecin hospitalier"
        sinistre_label = sinistre.numero_sinistre or f"sinistre #{sinistre.id}"
        hospital_name = stay.hospital.nom if stay.hospital else "l'hôpital"
        message = (
            f"📄 Rapport médical reçu\n\n"
            f"📋 Informations:\n"
            f"• Sinistre: {sinistre_label}\n"
            f"• Hôpital: {hospital_name}\n"
            f"• Médecin: {doctor_name}\n"
            f"• Le rapport médical a été transmis et nécessite votre validation."
        )
        await _notify_medical_referents(
            db,
            sinistre,
            "Rapport médical envoyé",
            message,
            type_notification="medical_report_submitted",
            push_queue=referent_push_queue,
        )

    db.commit()
    _dispatch_referent_push_queue(referent_push_queue)
    db.refresh(stay)
    return HospitalStayResponse.model_validate(stay)


@router.post(
    "/hospital-stays/{stay_id}/validation",
    response_model=HospitalStayResponse,
)
async def validate_hospital_stay_report(
    stay_id: int,
    payload: HospitalStayValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stay = db.query(HospitalStay).filter(HospitalStay.id == stay_id).first()
    if not stay:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Séjour introuvable")

    sinistre = stay.sinistre
    hospital = stay.hospital
    if not _user_is_referent_for_hospital(current_user, hospital, sinistre):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le médecin référent peut valider ce rapport.",
        )
    if stay.status not in {"awaiting_validation"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce séjour n'est pas en attente de validation.",
        )

    if payload.approve:
        stay.status = "validated"
        stay.report_status = "approved"
        stay.validated_at = datetime.utcnow()
        stay.validated_by_id = current_user.id
        stay.validation_notes = payload.notes
        accountants = _get_users_by_role(db, Role.AGENT_COMPTABLE_HOPITAL, stay.hospital_id)
        if accountants:
            _notify_users(
                db,
                accountants,
                "Rapport hospitalier validé",
                f"Le rapport du sinistre #{sinistre.numero_sinistre} est validé. Vous pouvez créer la facture.",
                relation_type="hospital_stay",
                relation_id=stay.id,
            )
    else:
        stay.status = "rejected"
        stay.report_status = "rejected"
        stay.validated_at = datetime.utcnow()
        stay.validated_by_id = current_user.id
        stay.validation_notes = payload.notes

    mark_notifications_read_for_relation(
        db,
        types=("medical_report_submitted",),
        lien_relation_type="sinistre",
        lien_relation_id=sinistre.id,
    )

    db.commit()
    db.refresh(stay)
    return HospitalStayResponse.model_validate(stay)


@router.get(
    "/hospital-stays/options",
    response_model=HospitalStayOptionsResponse,
)
async def get_hospital_stay_options():
    return HospitalStayOptionsResponse(actes=HOSPITAL_STAY_ACTS, examens=HOSPITAL_STAY_EXAMS)


@router.get(
    "/hospitals/{hospital_id}/doctors",
    response_model=List[HospitalStayDoctorSummary],
)
async def list_hospital_doctors(
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hôpital introuvable")

    allowed_roles = {Role.HOSPITAL_ADMIN, Role.AGENT_RECEPTION_HOPITAL, Role.MEDECIN_REFERENT_MH}
    role_val = _role_value(current_user)
    allowed_vals = {r.value for r in allowed_roles}
    if role_val not in allowed_vals or not _can_access_hospital(current_user, hospital):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")

    doctors = (
        db.query(User)
        .filter(
            User.hospital_id == hospital_id,
            User.is_active == True,
            User.role.in_([Role.DOCTOR, Role.MEDECIN_HOPITAL, Role.MEDECIN_REFERENT_MH]),
        )
        .order_by(User.full_name.asc())
        .all()
    )
    return [HospitalStayDoctorSummary.model_validate(doc) for doc in doctors]


@router.get(
    "/hospital-stays",
    response_model=List[HospitalStayResponse],
)
async def list_hospital_stays(
    status_filter: Optional[str] = Query(None, alias="status"),
    report_status: Optional[str] = Query(None),
    invoice_status: Optional[str] = Query(
        None,
        description="Filtrer sur le statut de la facture (utiliser 'none' pour les séjours sans facture)",
    ),
    hospital_id: Optional[int] = Query(
        None,
        description="Identifiant d'hôpital (requis pour les administrateurs)",
    ),
    search: Optional[str] = Query(
        None,
        min_length=2,
        description="Recherche par numéro de sinistre ou patient",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lister les séjours hospitaliers accessibles à l'utilisateur."""
    patient_alias = aliased(User)
    query = (
        db.query(HospitalStay)
        .options(
            joinedload(HospitalStay.assigned_doctor),
            joinedload(HospitalStay.patient),
            joinedload(HospitalStay.invoice),
            joinedload(HospitalStay.sinistre),
            joinedload(HospitalStay.hospital)
            .joinedload(Hospital.exam_tarifs),
            joinedload(HospitalStay.hospital)
            .joinedload(Hospital.act_tarifs),
        )
    )
    
    # Pour les utilisateurs normaux (patients), ils ne voient que leurs propres hospitalisations
    role_val = _role_value(current_user)
    if role_val == Role.USER.value:
        query = query.filter(HospitalStay.patient_id == current_user.id)
    elif role_val == Role.ADMIN.value:
        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le paramètre hospital_id est requis pour les administrateurs.",
            )
        hospital_ids = [hospital_id]
        query = query.filter(HospitalStay.hospital_id.in_(hospital_ids))
    else:
        # Pour les acteurs hospitaliers, utiliser la logique existante
        hospital_ids = _resolve_hospital_ids_for_user(db, current_user, hospital_id)
        query = query.filter(HospitalStay.hospital_id.in_(hospital_ids))

    if status_filter:
        query = query.filter(HospitalStay.status == status_filter)
    if report_status:
        query = query.filter(HospitalStay.report_status == report_status)
    if invoice_status:
        if invoice_status == "none":
            query = query.filter(HospitalStay.invoice == None)  # noqa: E711
        else:
            query = query.filter(
                HospitalStay.invoice.has(Invoice.statut == invoice_status)
            )
    if search:
        pattern = f"%{search.strip()}%"
        query = (
            query.outerjoin(Sinistre, HospitalStay.sinistre)
            .outerjoin(patient_alias, HospitalStay.patient)
            .filter(
                or_(
                    Sinistre.numero_sinistre.ilike(pattern),
                    patient_alias.full_name.ilike(pattern),
                    patient_alias.email.ilike(pattern),
                )
            )
        )

    stays = (
        query.order_by(HospitalStay.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [HospitalStayResponse.model_validate(stay) for stay in stays]


@router.get(
    "/hospital-stays/{stay_id}",
    response_model=HospitalStayResponse,
)
async def get_hospital_stay_detail(
    stay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulter le détail d'un séjour hospitalier."""
    query = (
        db.query(HospitalStay)
        .options(
            joinedload(HospitalStay.assigned_doctor),
            joinedload(HospitalStay.patient),
            joinedload(HospitalStay.invoice),
            joinedload(HospitalStay.sinistre),
            joinedload(HospitalStay.hospital)
            .joinedload(Hospital.exam_tarifs),
            joinedload(HospitalStay.hospital)
            .joinedload(Hospital.act_tarifs),
        )
        .filter(HospitalStay.id == stay_id)
    )

    if _role_value(current_user) != Role.ADMIN.value:
        hospital_ids = _resolve_hospital_ids_for_user(db, current_user)
        query = query.filter(HospitalStay.hospital_id.in_(hospital_ids))

    stay = query.first()
    if not stay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Séjour introuvable ou inaccessible.",
        )

    return HospitalStayResponse.model_validate(stay)


@router.post(
    "/hospital-stays/{stay_id}/invoice",
    response_model=HospitalStayResponse,
)
async def create_invoice_for_stay(
    stay_id: int,
    payload: HospitalStayInvoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stay = (
        db.query(HospitalStay)
        .options(
            joinedload(HospitalStay.hospital)
            .joinedload(Hospital.exam_tarifs),
            joinedload(HospitalStay.hospital)
            .joinedload(Hospital.act_tarifs),
        )
        .filter(HospitalStay.id == stay_id)
        .first()
    )
    if not stay:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Séjour introuvable")

    sinistre = stay.sinistre
    _require_hospital_actor(
        current_user,
        sinistre,
        {Role.HOSPITAL_ADMIN, Role.AGENT_COMPTABLE_HOPITAL},
    )
    if stay.status != "validated":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le rapport doit être validé avant la facturation.",
        )
    if stay.invoice:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Une facture a déjà été générée.")

    custom_lines = None
    if payload.lines:
        custom_lines = []
        for item in payload.lines:
            quantity = int(item.quantite)
            unit_price = item.prix_unitaire.quantize(Decimal("0.01"))
            montant_ht = (unit_price * Decimal(quantity)).quantize(Decimal("0.01"))
            custom_lines.append(
                {
                    "libelle": item.libelle,
                    "quantite": quantity,
                    "prix_unitaire": unit_price,
                    "montant_ht": montant_ht,
                }
            )

    lines = custom_lines if custom_lines is not None else _prepare_invoice_lines(stay)
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de générer une facture sans durée, actes ou examens.",
        )

    taux_tva = payload.taux_tva
    montant_ht = sum(line["montant_ht"] for line in lines)
    montant_tva = (montant_ht * taux_tva).quantize(Decimal("0.01"))
    montant_ttc = montant_ht + montant_tva

    numero_facture = f"INV-STAY-{stay.hospital_id}-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    invoice = Invoice(
        hospital_id=stay.hospital_id,
        hospital_stay_id=stay.id,
        numero_facture=numero_facture,
        montant_ht=montant_ht,
        montant_tva=montant_tva,
        montant_ttc=montant_ttc,
        date_facture=datetime.utcnow(),
        statut=InvoiceStatus.PENDING_MEDICAL,
        validation_medicale="pending",
        validation_sinistre=None,
        validation_compta=None,
        notes=payload.notes,
    )
    db.add(invoice)
    db.flush()

    for line in lines:
        db.add(
            InvoiceItem(
                invoice_id=invoice.id,
                libelle=line["libelle"],
                quantite=line["quantite"],
                prix_unitaire=line["prix_unitaire"],
                montant_ht=line["montant_ht"],
                taux_tva=taux_tva,
                montant_ttc=line["montant_ht"] * (Decimal("1") + taux_tva),
            )
        )

    stay.status = "invoiced"
    record_invoice_history(
        db,
        invoice,
        action="invoice_created",
        actor_id=current_user.id,
        notes=payload.notes,
    )

    medical_reviewers = _get_active_users_by_roles(
        db,
        {Role.MEDICAL_REVIEWER, Role.MEDECIN_REFERENT_MH},
    )
    if medical_reviewers:
        hospital_name = stay.hospital.nom if stay.hospital else "l'hôpital"
        sinistre_label = sinistre.numero_sinistre or f"sinistre #{sinistre.id}"
        message = (
            f"💼 Facture à valider\n\n"
            f"📋 Informations:\n"
            f"• Facture: #{invoice.numero_facture}\n"
            f"• Sinistre: {sinistre_label}\n"
            f"• Hôpital: {hospital_name}\n"
            f"• Montant TTC: {invoice.montant_ttc:.2f} FCFA\n"
            f"• Cette facture nécessite votre validation médicale."
        )
        _notify_users(
            db,
            medical_reviewers,
            "Accord médical requis",
            message,
            relation_type="invoice",
            relation_id=invoice.id,
            type_notification="invoice_medical_review",
            send_push_channel=True,
        )
    
    # Notifier les agents SOS operator
    sos_operators = _get_active_users_by_roles(
        db,
        {Role.SOS_OPERATOR},
    )
    if sos_operators:
        hospital = stay.hospital
        hospital_name = hospital.nom if hospital else "Hôpital inconnu"
        _notify_users(
            db,
            sos_operators,
            "Nouvelle facture reçue",
            f"📋 Informations:\n• Facture: #{invoice.numero_facture}\n• Hôpital: {hospital_name}\n• Montant TTC: {invoice.montant_ttc:.2f} FCFA\n• Statut: En attente de validation médicale",
            relation_type="invoice",
            relation_id=invoice.id,
            type_notification="invoice_received",
            send_push_channel=True,
        )

    db.commit()
    db.refresh(stay)
    return HospitalStayResponse.model_validate(stay)

