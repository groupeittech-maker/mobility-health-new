"""Workflows médicaux — rapports d'étape, double validation, escalade MC → AM.

- Médecin-conseil (MC) : 1re validation hospitalisations/rapatriements/rapports/factures.
- Affaires médicales (AM) : 2e validation + « 2e possibilité » quand le MC est indisponible
  (escalade automatique après MEDECIN_CONSEIL_ESCALATION_MINUTES).
"""
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.alerte import Alerte
from app.models.alerte_ops import AlerteEvent
from app.models.hospital_stay import HospitalStay
from app.models.medical_workflow import HospitalMedicalReport
from app.models.mhc_care_document import MhcCareDocument
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

ESCALATION_MINUTES = int(os.getenv("MEDECIN_CONSEIL_ESCALATION_MINUTES", "30"))

MC_ROLES = {"medecin_referent_mh"}
AM_ROLES = {"superviseur_affaires_medicales", "agent_medical_mhc", "agent_conformite_medical", "medical_reviewer"}
PARTNER_ROLES = {"medecin_hopital", "hospital_admin", "agent_reception_hopital"}


def _role_str(current_user) -> str:
    role = getattr(current_user, "role", "user")
    if hasattr(role, "value"):
        role = role.value
    return str(role or "user")


def _is_admin(current_user) -> bool:
    return _role_str(current_user) == "admin" or getattr(current_user, "is_superuser", False)


def _actor_name(current_user) -> str:
    return getattr(current_user, "full_name", None) or getattr(current_user, "username", None) or ""


def _log_alerte(db: Session, alerte_id: int, event_type: str, label: str, current_user=None) -> None:
    db.add(AlerteEvent(
        alerte_id=alerte_id,
        event_type=event_type,
        label=label,
        actor_id=getattr(current_user, "id", None),
        actor_name=_actor_name(current_user),
    ))


def escalate_overdue(db: Session) -> int:
    """Réassigne aux affaires médicales les éléments bloqués chez le médecin-conseil."""
    cutoff = datetime.utcnow() - timedelta(minutes=ESCALATION_MINUTES)
    count = 0
    # Alertes assignées au médecin-conseil sans réponse.
    for alerte in (
        db.query(Alerte)
        .filter(
            Alerte.assigned_role == "medecin_conseil",
            Alerte.assigned_at < cutoff,
            Alerte.statut.in_(["en_attente", "en_cours"]),
        )
        .all()
    ):
        alerte.assigned_role = "affaires_medicales"
        db.add(AlerteEvent(
            alerte_id=alerte.id,
            event_type="escalade",
            label=f"Escalade automatique vers les affaires médicales (délai {ESCALATION_MINUTES} min dépassé)",
        ))
        count += 1
    # Rapports en attente de 1re validation.
    for report in (
        db.query(HospitalMedicalReport)
        .filter(HospitalMedicalReport.statut == "soumis", HospitalMedicalReport.created_at < cutoff, HospitalMedicalReport.escalated == False)
        .all()
    ):
        report.escalated = True
        count += 1
    if count:
        db.flush()
    return count


class MedicalReportCreate(BaseModel):
    report_type: str = "etape"  # etape | final
    resume: Optional[str] = None
    actes: Optional[list] = None
    examens: Optional[list] = None
    observations: Optional[str] = None
    evolution: Optional[str] = None


class ValidationPayload(BaseModel):
    decision: str  # accorde | refuse
    commentaire: Optional[str] = None


def _get_stay_or_404(db: Session, stay_id: int) -> HospitalStay:
    stay = db.query(HospitalStay).filter(HospitalStay.id == stay_id).first()
    if not stay:
        raise HTTPException(status_code=404, detail="Séjour introuvable")
    return stay


def _check_partner_access(current_user, stay: HospitalStay) -> None:
    if _is_admin(current_user):
        return
    role = _role_str(current_user)
    if role in PARTNER_ROLES:
        if getattr(current_user, "hospital_id", None) == stay.hospital_id:
            return
        raise HTTPException(status_code=403, detail="Séjour hors de votre établissement")
    if role in MC_ROLES | AM_ROLES:
        return
    raise HTTPException(status_code=403, detail="Accès non autorisé")


@router.post("/hospital-stays/{stay_id}/medical-reports", status_code=status.HTTP_201_CREATED)
async def create_medical_report(
    stay_id: int,
    payload: MedicalReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rapport médical d'étape ou final, émis par le partenaire-santé."""
    stay = _get_stay_or_404(db, stay_id)
    _check_partner_access(current_user, stay)
    if payload.report_type not in ("etape", "final"):
        raise HTTPException(status_code=400, detail="report_type doit être 'etape' ou 'final'")
    report = HospitalMedicalReport(
        stay_id=stay_id,
        report_type=payload.report_type,
        resume=payload.resume,
        actes=payload.actes,
        examens=payload.examens,
        observations=payload.observations,
        evolution=payload.evolution,
        created_by_id=current_user.id,
    )
    db.add(report)
    sinistre = stay.sinistre
    if sinistre:
        _log_alerte(db, sinistre.alerte_id, "rapport", f"Rapport médical ({payload.report_type}) soumis", current_user)
    db.commit()
    db.refresh(report)
    return _report_to_dict(report)


@router.get("/hospital-stays/{stay_id}/medical-reports")
async def list_medical_reports(
    stay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stay = _get_stay_or_404(db, stay_id)
    _check_partner_access(current_user, stay)
    reports = (
        db.query(HospitalMedicalReport)
        .filter(HospitalMedicalReport.stay_id == stay_id)
        .order_by(HospitalMedicalReport.created_at.asc())
        .all()
    )
    return [_report_to_dict(r) for r in reports]


def _report_to_dict(r: HospitalMedicalReport) -> dict:
    return {
        "id": r.id,
        "stay_id": r.stay_id,
        "report_type": r.report_type,
        "resume": r.resume,
        "actes": r.actes,
        "examens": r.examens,
        "observations": r.observations,
        "evolution": r.evolution,
        "statut": r.statut,
        "escalated": r.escalated,
        "created_by_id": r.created_by_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "validated_mc_at": r.validated_mc_at.isoformat() if r.validated_mc_at else None,
        "validated_am_at": r.validated_am_at.isoformat() if r.validated_am_at else None,
        "refusal_reason": r.refusal_reason,
    }


@router.post("/medical-reports/{report_id}/validate")
async def validate_medical_report(
    report_id: int,
    payload: ValidationPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Double validation : niveau 1 = médecin-conseil, niveau 2 = affaires médicales.
    Les AM reprennent le niveau 1 quand le rapport est escaladé (2e possibilité)."""
    report = db.query(HospitalMedicalReport).filter(HospitalMedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    if payload.decision not in ("accorde", "refuse"):
        raise HTTPException(status_code=400, detail="decision doit être 'accorde' ou 'refuse'")

    role = _role_str(current_user)
    admin = _is_admin(current_user)
    now = datetime.utcnow()
    stay = report.stay
    sinistre = stay.sinistre if stay else None

    if report.statut == "soumis":
        # Niveau 1 — MC, ou AM si escaladé (médecin-conseil indisponible).
        if role in MC_ROLES or admin:
            pass
        elif role in AM_ROLES and report.escalated:
            pass
        else:
            raise HTTPException(status_code=403, detail="1re validation réservée au médecin-conseil")
        if payload.decision == "refuse":
            report.statut = "refusee"
            report.refusal_reason = payload.commentaire
        else:
            report.statut = "validee_mc"
        report.validated_mc_by_id = current_user.id
        report.validated_mc_at = now
        if sinistre:
            _log_alerte(db, sinistre.alerte_id, "validation",
                        f"Rapport {report.report_type} : 1re validation ({payload.decision})", current_user)

    elif report.statut == "validee_mc":
        # Niveau 2 — affaires médicales uniquement.
        if not (role in AM_ROLES or admin):
            raise HTTPException(status_code=403, detail="2e validation réservée aux affaires médicales")
        if payload.decision == "refuse":
            report.statut = "refusee"
            report.refusal_reason = payload.commentaire
        else:
            report.statut = "validee_am"
        report.validated_am_by_id = current_user.id
        report.validated_am_at = now
        if sinistre:
            _log_alerte(db, sinistre.alerte_id, "validation",
                        f"Rapport {report.report_type} : 2e validation ({payload.decision})", current_user)
    else:
        raise HTTPException(status_code=400, detail=f"Rapport déjà traité (statut {report.statut})")

    db.commit()
    db.refresh(report)
    return _report_to_dict(report)


@router.get("/validations/pending")
async def pending_validations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """File de validations du profil appelant (MC : niveau 1 ; AM : niveau 2 + escalades).
    Déclenche aussi l'escalade des éléments bloqués chez le médecin-conseil."""
    role = _role_str(current_user)
    if not (_is_admin(current_user) or role in MC_ROLES or role in AM_ROLES):
        raise HTTPException(status_code=403, detail="Profil non habilité aux validations médicales")
    escalate_overdue(db)
    db.commit()

    is_am = role in AM_ROLES or _is_admin(current_user)
    is_mc = role in MC_ROLES or _is_admin(current_user)

    reports_q = db.query(HospitalMedicalReport)
    if is_mc and not is_am:
        reports = reports_q.filter(HospitalMedicalReport.statut == "soumis").all()
    elif is_am and not is_mc:
        reports = reports_q.filter(
            or_(
                HospitalMedicalReport.statut == "validee_mc",
                (HospitalMedicalReport.statut == "soumis") & (HospitalMedicalReport.escalated == True),
            )
        ).all()
    else:  # admin voit tout
        reports = reports_q.filter(HospitalMedicalReport.statut.in_(["soumis", "validee_mc"])).all()

    # Documents de prise en charge en attente de validation du groupe appelant.
    from app.core.mhc_nomenclature import MhcCareDocumentType
    from app.services.mhc_care_document_service import required_validator_groups, GROUP_MEDECIN_CONSEIL, GROUP_POLE_MEDICAL_MHC
    care_pending = []
    docs = db.query(MhcCareDocument).filter(MhcCareDocument.validation_status == "en_attente").all()
    for doc in docs:
        try:
            groups = required_validator_groups(MhcCareDocumentType(doc.document_type))
        except Exception:
            groups = []
        already = {v.get("group") for v in (doc.validations or [])}
        missing = [g for g in groups if g not in already]
        if not missing:
            continue
        next_group = missing[0]
        if (is_mc and next_group == GROUP_MEDECIN_CONSEIL) or (is_am and next_group == GROUP_POLE_MEDICAL_MHC):
            care_pending.append({
                "document_id": doc.id,
                "sinistre_id": doc.sinistre_id,
                "document_type": doc.document_type,
                "numero": doc.numero,
                "groupe_attendu": next_group,
                "issued_at": doc.issued_at.isoformat() if doc.issued_at else None,
            })

    return {
        "escalations_applied": True,
        "reports": [_report_to_dict(r) for r in reports],
        "care_documents": care_pending,
    }
