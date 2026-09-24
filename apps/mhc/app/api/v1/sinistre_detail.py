"""Détail sinistre enrichi — vue « Détail du sinistre » du back-office.

- GET /sinistres/{id}/detail-complet : toutes les infos de l'écran
- GET /sinistres/{id}/parcours : matrice parties prenantes × étapes (A/R)
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.mhc_nomenclature import MhcCareDocumentType, DOCUMENT_TITLES
from app.core.permissions import (
    F_SINISTRES,
    LEVEL_CONSULTATION,
    has_permission,
)
from app.models.alerte import Alerte
from app.models.alerte_ops import AlerteEvent
from app.models.hospital_stay import HospitalStay
from app.models.invoice import Invoice
from app.models.medical_workflow import HospitalMedicalReport
from app.models.mhc_care_document import MhcCareDocument
from app.models.ops_modules import TransportMission
from app.models.sinistre import Sinistre
from app.models.sinistre_attachment import SinistreAttachment
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def _role_str(u) -> str:
    r = getattr(u, "role", "user")
    return getattr(r, "value", r) or "user"


STAFF_PREFIXES = (
    "admin", "superviseur_", "agent_", "production_agent", "sos_operator",
    "medical_reviewer", "technical_reviewer", "finance_manager",
    "medecin_referent_mh", "medecin_hopital", "hospital_admin",
    "assistant_souscription",
)


def _check_access(db: Session, current_user, sinistre: Sinistre) -> None:
    role = _role_str(current_user)
    if role == "user":
        souscription = sinistre.souscription
        if souscription and souscription.user_id == current_user.id:
            return
        raise HTTPException(status_code=403, detail="Accès refusé")
    if role in ("agent_reception_hopital", "medecin_hopital", "hospital_admin", "agent_comptable_hopital"):
        hid = getattr(current_user, "hospital_id", None)
        if hid and hid == sinistre.hospital_id:
            return
        raise HTTPException(status_code=403, detail="Sinistre hors de votre établissement")
    if not (role.startswith(STAFF_PREFIXES) or has_permission(role, F_SINISTRES, LEVEL_CONSULTATION)):
        raise HTTPException(status_code=403, detail="Accès refusé")


def _get_sinistre(db: Session, sinistre_id: int) -> Sinistre:
    s = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sinistre introuvable")
    return s


def _user_brief(u: Optional[User]) -> Optional[dict]:
    if not u:
        return None
    return {
        "id": u.id,
        "nom": getattr(u, "full_name", None) or getattr(u, "username", None),
        "email": getattr(u, "email", None),
        "telephone": getattr(u, "telephone", None),
        "date_naissance": str(getattr(u, "date_naissance", None) or "") or None,
        "nationalite": getattr(u, "nationalite", None),
        "numero_passeport": getattr(u, "numero_passeport", None),
        "photo_url": getattr(u, "photo_url", None),
    }


@router.get("/sinistres/{sinistre_id}/detail-complet")
async def sinistre_detail(
    sinistre_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sinistre = _get_sinistre(db, sinistre_id)
    _check_access(db, current_user, sinistre)

    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first()
    souscription = sinistre.souscription
    patient = None
    if souscription and souscription.user_id:
        patient = db.query(User).filter(User.id == souscription.user_id).first()
    elif alerte:
        patient = db.query(User).filter(User.id == alerte.user_id).first()

    stay = db.query(HospitalStay).filter(HospitalStay.sinistre_id == sinistre_id).first()
    docs = (
        db.query(MhcCareDocument)
        .filter(MhcCareDocument.sinistre_id == sinistre_id)
        .order_by(MhcCareDocument.issued_at.desc())
        .all()
    )
    attachments = (
        db.query(SinistreAttachment).filter(SinistreAttachment.sinistre_id == sinistre_id).all()
    )
    reports = []
    invoice = None
    if stay:
        reports = (
            db.query(HospitalMedicalReport)
            .filter(HospitalMedicalReport.stay_id == stay.id)
            .order_by(HospitalMedicalReport.created_at.asc())
            .all()
        )
        invoice = db.query(Invoice).filter(Invoice.hospital_stay_id == stay.id).first()

    events = []
    if alerte:
        events = (
            db.query(AlerteEvent)
            .filter(AlerteEvent.alerte_id == alerte.id)
            .order_by(AlerteEvent.created_at.asc())
            .all()
        )

    medecin = None
    if sinistre.medecin_referent_id:
        medecin = db.query(User).filter(User.id == sinistre.medecin_referent_id).first()

    return {
        "sinistre": {
            "id": sinistre.id,
            "numero": sinistre.numero_sinistre or f"SIN-{sinistre.id}",
            "statut": sinistre.statut,
            "description": sinistre.description,
            "created_at": sinistre.created_at.isoformat() if sinistre.created_at else None,
            "medecin_referent": _user_brief(medecin),
        },
        "alerte": {
            "id": alerte.id,
            "numero": alerte.numero_alerte or f"URG-{alerte.id}",
            "type_urgence": getattr(alerte, "type_urgence", None) or getattr(alerte, "type_sinistre", None),
            "description": alerte.description,
            "adresse": alerte.adresse,
            "priorite": alerte.priorite,
            "latitude": float(alerte.latitude) if alerte.latitude else None,
            "longitude": float(alerte.longitude) if alerte.longitude else None,
            "statut": alerte.statut,
            "created_at": alerte.created_at.isoformat() if alerte.created_at else None,
        } if alerte else None,
        "souscription": {
            "id": souscription.id,
            "numero": souscription.numero_souscription,
            "produit": souscription.produit_assurance.nom if souscription.produit_assurance else None,
            "date_debut": str(souscription.date_debut) if souscription.date_debut else None,
            "date_fin": str(souscription.date_fin) if souscription.date_fin else None,
            "destination": getattr(souscription, "destination", None),
        } if souscription else None,
        "assure": _user_brief(patient),
        "hospital": {
            "id": sinistre.hospital.id,
            "nom": sinistre.hospital.nom,
            "ville": getattr(sinistre.hospital, "ville", None),
            "pays": getattr(sinistre.hospital, "pays", None),
        } if sinistre.hospital else None,
        "stay": {
            "id": stay.id,
            "status": stay.status,
            "service": stay.service_concerne,
            "chambre": stay.chambre,
            "started_at": stay.started_at.isoformat() if stay.started_at else None,
            "ended_at": stay.ended_at.isoformat() if stay.ended_at else None,
            "report_motif_consultation": stay.report_motif_consultation,
            "report_motif_hospitalisation": stay.report_motif_hospitalisation,
            "report_resume": stay.report_resume,
            "report_observations": stay.report_observations,
        } if stay else None,
        "care_documents": [
            {
                "id": d.id,
                "type": d.document_type,
                "titre": DOCUMENT_TITLES.get(d.document_type if isinstance(d.document_type, MhcCareDocumentType) else _safe_doc_type(d.document_type), d.document_type),
                "numero": d.numero,
                "statut": d.statut,
                "validation_status": d.validation_status,
                "issued_at": d.issued_at.isoformat() if d.issued_at else None,
                "validations": d.validations or [],
            }
            for d in docs
        ],
        "attachments": [
            {"id": a.id, "filename": a.file_name, "type": a.attachment_type, "size": a.file_size}
            for a in attachments
        ],
        "medical_reports": [
            {
                "id": r.id, "type": r.report_type, "statut": r.statut,
                "resume": r.resume, "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ],
        "invoice": {
            "id": invoice.id,
            "numero": getattr(invoice, "numero", None),
            "montant_ttc": float(invoice.montant_ttc),
            "statut": invoice.statut,
        } if invoice else None,
        "historique": [
            {
                "type": e.event_type,
                "label": e.label,
                "actor": e.actor_name,
                "at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


def _safe_doc_type(value):
    try:
        return MhcCareDocumentType(value)
    except Exception:
        return value


# ---------------------------------------------------------------------------
# Matrice « Parcours de prise en charge »
# ---------------------------------------------------------------------------

PARTIES = [
    {"key": "medecin_conseil", "label": "Médecin conseil"},
    {"key": "partenaire_sante", "label": "Hôpital / Clinique"},
    {"key": "affaires_medicales", "label": "Affaires médicales"},
]

ETAPES = [
    {"key": "appel_urgence", "label": "Appel urgence"},
    {"key": "transport_medical", "label": "Transport médical"},
    {"key": "prise_en_charge_urgence", "label": "Prise en charge urgence"},
    {"key": "hospitalisation", "label": "Hospitalisation"},
    {"key": "prolongation_hospitalisation", "label": "Prolongation hospitalisation"},
    {"key": "bulletin_sortie", "label": "Bulletin de sortie"},
    {"key": "rapatriement_sanitaire", "label": "Rapatriement sanitaire"},
    {"key": "rapatriement_funeraire", "label": "Rapatriement funéraire"},
    {"key": "suivi_medical", "label": "Suivi médical"},
]

# Étape → type(s) de document de prise en charge associé.
ETAPE_DOC_TYPES = {
    "prise_en_charge_urgence": ["bpcu"],
    "hospitalisation": ["bh"],
    "prolongation_hospitalisation": ["bph"],
    "bulletin_sortie": ["bs"],
    "rapatriement_sanitaire": ["brs", "ars"],
    "rapatriement_funeraire": ["brf", "arf"],
}

# Groupe de validation → partie prenante de la matrice.
GROUP_TO_PARTIE = {
    "medecin_conseil": "medecin_conseil",
    "partenaire_sante": "partenaire_sante",
    "pole_medical_mhc": "affaires_medicales",
}

# Émetteur de chaque type de document → partie prenante.
DOC_EMITTER_PARTIE = {
    "bpcu": "medecin_conseil",
    "brpcu": "medecin_conseil",
    "bh": "partenaire_sante",
    "bph": "partenaire_sante",
    "bs": "partenaire_sante",
    "brs": "medecin_conseil",
    "brf": "medecin_conseil",
    "ars": "affaires_medicales",
    "arf": "affaires_medicales",
}


@router.get("/sinistres/{sinistre_id}/parcours")
async def sinistre_parcours(
    sinistre_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Matrice parties prenantes × étapes. Cellule : 'A' (accepté), 'R' (refusé), '—' (non concerné/en attente)."""
    sinistre = _get_sinistre(db, sinistre_id)
    _check_access(db, current_user, sinistre)

    docs = db.query(MhcCareDocument).filter(MhcCareDocument.sinistre_id == sinistre_id).all()
    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first()
    missions = db.query(TransportMission).filter(TransportMission.sinistre_id == sinistre_id).all()
    stay = db.query(HospitalStay).filter(HospitalStay.sinistre_id == sinistre_id).first()
    reports = (
        db.query(HospitalMedicalReport).filter(HospitalMedicalReport.stay_id == stay.id).all()
        if stay else []
    )

    cells = {p["key"]: {e["key"]: "—" for e in ETAPES} for p in PARTIES}

    # Appel urgence : l'alerte a été reçue → médecin-conseil en charge.
    if alerte:
        cells["medecin_conseil"]["appel_urgence"] = "A"

    # Transport médical : mission créée (par l'hôpital ou MHC).
    if missions:
        cells["partenaire_sante"]["transport_medical"] = "A"
        if sinistre.alerte_id:
            cells["medecin_conseil"]["transport_medical"] = "A"

    # Documents de prise en charge.
    doc_by_type = {}
    for d in docs:
        dt = d.document_type if isinstance(d.document_type, str) else getattr(d.document_type, "value", str(d.document_type))
        doc_by_type.setdefault(dt, []).append(d)

    for etape_key, doc_types in ETAPE_DOC_TYPES.items():
        for dt in doc_types:
            for d in doc_by_type.get(dt, []):
                emitter = DOC_EMITTER_PARTIE.get(dt)
                if emitter and cells[emitter][etape_key] == "—":
                    cells[emitter][etape_key] = "A"
                # Validations par groupe → A/R sur la partie correspondante.
                for v in d.validations or []:
                    partie = GROUP_TO_PARTIE.get(v.get("groupe"))
                    if partie:
                        cells[partie][etape_key] = "A" if v.get("approuve") else "R"

    # Refus de prise en charge : BRPCU → médecin-conseil a refusé.
    if doc_by_type.get("brpcu"):
        cells["medecin_conseil"]["prise_en_charge_urgence"] = "R"

    # Suivi médical : rapports d'étape du partenaire + validations MC/AM.
    if reports:
        cells["partenaire_sante"]["suivi_medical"] = "A"
        for r in reports:
            if r.statut == "refusee":
                if r.validated_am_by_id:
                    cells["affaires_medicales"]["suivi_medical"] = "R"
                elif r.validated_mc_by_id:
                    cells["medecin_conseil"]["suivi_medical"] = "R"
            elif r.statut == "validee_mc":
                cells["medecin_conseil"]["suivi_medical"] = "A"
            elif r.statut == "validee_am":
                cells["medecin_conseil"]["suivi_medical"] = "A"
                cells["affaires_medicales"]["suivi_medical"] = "A"

    return {
        "sinistre_id": sinistre_id,
        "parties": PARTIES,
        "etapes": ETAPES,
        "cells": cells,
    }
