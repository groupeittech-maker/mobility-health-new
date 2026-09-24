"""Centre d'alertes urgence — opérations de traitement d'une alerte SOS.

Endpoints consommés par l'écran « Détails de l'alerte » (maquette back-office) :
stepper Réception → Évaluation → Orientation → Prise en charge → Suivi → Clôture,
établissements à proximité, statut médical, notes, timeline, transfert,
notification hôpital.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.api.v1.sos import (
    _build_alertes_query_for_user,
    calculate_distance,
    generate_numero_sinistre,
    notify_hospital_reception,
)
from app.core.database import get_db
from app.core.permissions import F_ALERTE_SOS, LEVEL_CONSULTATION, LEVEL_EDITION, has_permission
from app.models.alerte import Alerte
from app.models.alerte_ops import AlerteEvent, AlerteNote, AlerteStatutMedical
from app.models.hospital import Hospital
from app.models.hospital_stay import HospitalStay
from app.models.mhc_care_document import MhcCareDocument
from app.models.sinistre import Sinistre
from app.models.sinistre_attachment import SinistreAttachment
from app.models.souscription import Souscription
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

ALERTE_STATUTS = {"en_attente", "en_cours", "resolue", "annulee"}


def _role_str(current_user) -> str:
    role = getattr(current_user, "role", "user")
    if hasattr(role, "value"):
        role = role.value
    return str(role or "user")


def _require_alerte(db: Session, alerte_id: int, current_user, min_level: str) -> Alerte:
    """Charge l'alerte après contrôle de permission + scope existant."""
    role = _role_str(current_user)
    feature_level = LEVEL_EDITION if min_level == LEVEL_EDITION else LEVEL_CONSULTATION
    if not has_permission(role, F_ALERTE_SOS, feature_level):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission insuffisante sur les alertes SOS")
    alerte = db.query(Alerte).filter(Alerte.id == alerte_id).first()
    if not alerte:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte introuvable")
    # Les profils hôpitaux restent limités aux alertes de leur établissement.
    hospital_roles = {"hospital_admin", "agent_reception_hopital", "medecin_hopital", "agent_comptable_hopital"}
    if role in hospital_roles:
        allowed = _build_alertes_query_for_user(db, current_user)
        if not allowed.filter(Alerte.id == alerte_id).first():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Alerte hors de votre établissement")
    return alerte


def _log_event(db: Session, alerte_id: int, event_type: str, label: str, current_user=None, details: dict = None) -> None:
    db.add(AlerteEvent(
        alerte_id=alerte_id,
        event_type=event_type,
        label=label,
        details=details,
        actor_id=getattr(current_user, "id", None),
        actor_name=getattr(current_user, "full_name", None) or getattr(current_user, "username", None),
    ))


def _get_sinistre(db: Session, alerte_id: int) -> Optional[Sinistre]:
    return (
        db.query(Sinistre)
        .filter(Sinistre.alerte_id == alerte_id)
        .order_by(Sinistre.id.desc())
        .first()
    )


def _current_step(db: Session, alerte: Alerte, sinistre: Optional[Sinistre]) -> int:
    """Position dans le stepper : 1 Réception … 6 Clôture."""
    if alerte.statut == "resolue":
        return 6
    step = 1
    if alerte.statut != "en_attente":
        step = 2
    if sinistre and sinistre.hospital_id:
        step = 3
    if sinistre:
        has_bpcu = (
            db.query(MhcCareDocument)
            .filter(MhcCareDocument.sinistre_id == sinistre.id, MhcCareDocument.document_type == "BPCU")
            .first()
        )
        if has_bpcu:
            step = 4
        has_stay = db.query(HospitalStay).filter(HospitalStay.sinistre_id == sinistre.id).first()
        if has_stay:
            step = 5
    return step


def _assure_payload(alerte: Alerte, souscription: Optional[Souscription]) -> dict:
    u = alerte.user
    if not u:
        return {}
    age = None
    dob = getattr(u, "date_naissance", None)
    if dob:
        try:
            today = datetime.utcnow().date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except Exception:
            age = None
    produit_nom = None
    date_debut = date_fin = None
    if souscription:
        produit = getattr(souscription, "produit", None)
        produit_nom = getattr(produit, "nom", None) if produit else getattr(souscription, "produit_nom", None)
        date_debut = getattr(souscription, "date_debut", None)
        date_fin = getattr(souscription, "date_fin", None)
    return {
        "id": u.id,
        "nom": u.full_name or u.username,
        "email": u.email,
        "telephone": getattr(u, "telephone", None),
        "date_naissance": dob.isoformat() if dob else None,
        "age": age,
        "nationalite": getattr(u, "nationalite", None),
        "numero_passeport": getattr(u, "numero_passeport", None),
        "sexe": getattr(u, "sexe", None),
        "numero_assure": getattr(souscription, "numero_souscription", None) if souscription else None,
        "type_contrat": produit_nom,
        "date_debut_couverture": date_debut.isoformat() if hasattr(date_debut, "isoformat") else date_debut,
        "date_fin_couverture": date_fin.isoformat() if hasattr(date_fin, "isoformat") else date_fin,
        "contact_urgence": getattr(u, "contact_urgence", None),
        "nom_contact_urgence": getattr(u, "nom_contact_urgence", None),
    }


def _documents_payload(db: Session, sinistre: Optional[Sinistre]) -> List[dict]:
    docs = []
    if not sinistre:
        return docs
    for att in db.query(SinistreAttachment).filter(SinistreAttachment.sinistre_id == sinistre.id).all():
        docs.append({
            "id": att.id,
            "type": att.attachment_type,
            "file_name": att.file_name,
            "content_type": att.content_type,
            "url": f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/attachments/{att.id}/download",
        })
    return docs


class NoteCreate(BaseModel):
    note: str


class StatutUpdate(BaseModel):
    statut: str
    commentaire: Optional[str] = None


class StatutMedicalUpdate(BaseModel):
    etat_patient: Optional[str] = None
    motifs_symptomes: Optional[str] = None
    besoins_immediats: Optional[str] = None
    allergies_connues: Optional[str] = None
    traitements_en_cours: Optional[str] = None


class TransferRequest(BaseModel):
    cible: str  # 'affaires_medicales' | 'medecin_conseil' | 'user:<id>'
    commentaire: Optional[str] = None


class NotifyHospitalRequest(BaseModel):
    hospital_id: int


class ActionRequest(BaseModel):
    action: str  # 'ambulance' | 'prise_en_charge' | 'hotel'
    notes: Optional[str] = None


@router.get("/{alerte_id}/detail-complet")
async def get_alerte_detail_complet(
    alerte_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Vue agrégée de l'alerte pour l'écran de traitement (maquette centre d'alertes)."""
    alerte = _require_alerte(db, alerte_id, current_user, LEVEL_CONSULTATION)
    sinistre = _get_sinistre(db, alerte_id)
    souscription = db.query(Souscription).filter(Souscription.id == alerte.souscription_id).first() if alerte.souscription_id else None

    statut_medical = db.query(AlerteStatutMedical).filter(AlerteStatutMedical.alerte_id == alerte_id).first()
    notes = (
        db.query(AlerteNote)
        .filter(AlerteNote.alerte_id == alerte_id)
        .order_by(AlerteNote.created_at.desc())
        .all()
    )
    events = (
        db.query(AlerteEvent)
        .filter(AlerteEvent.alerte_id == alerte_id)
        .order_by(AlerteEvent.created_at.asc())
        .all()
    )
    if not events:
        _log_event(db, alerte_id, "reception", "Alerte reçue", None)
        db.commit()
        events = db.query(AlerteEvent).filter(AlerteEvent.alerte_id == alerte_id).order_by(AlerteEvent.created_at.asc()).all()

    hospital = db.query(Hospital).filter(Hospital.id == sinistre.hospital_id).first() if sinistre and sinistre.hospital_id else None
    medecin = db.query(User).filter(User.id == sinistre.medecin_referent_id).first() if sinistre and sinistre.medecin_referent_id else None

    return {
        "alerte": {
            "id": alerte.id,
            "numero_alerte": alerte.numero_alerte,
            "statut": alerte.statut,
            "priorite": alerte.priorite,
            "latitude": float(alerte.latitude),
            "longitude": float(alerte.longitude),
            "adresse": alerte.adresse,
            "description": alerte.description,
            "created_at": alerte.created_at.isoformat() if alerte.created_at else None,
        },
        "etape_courante": _current_step(db, alerte, sinistre),
        "assure": _assure_payload(alerte, souscription),
        "statut_medical": (
            {
                "etat_patient": statut_medical.etat_patient,
                "motifs_symptomes": statut_medical.motifs_symptomes,
                "besoins_immediats": statut_medical.besoins_immediats,
                "allergies_connues": statut_medical.allergies_connues,
                "traitements_en_cours": statut_medical.traitements_en_cours,
                "updated_by_name": statut_medical.updated_by_name,
                "updated_at": statut_medical.updated_at.isoformat() if statut_medical.updated_at else None,
            }
            if statut_medical else None
        ),
        "hospital_assigne": (
            {"id": hospital.id, "nom": hospital.nom, "adresse": hospital.adresse, "ville": hospital.ville, "telephone": hospital.telephone}
            if hospital else None
        ),
        "medecin_referent": (
            {"id": medecin.id, "nom": medecin.full_name or medecin.username, "telephone": getattr(medecin, "telephone", None)}
            if medecin else None
        ),
        "sinistre_id": sinistre.id if sinistre else None,
        "numero_sinistre": sinistre.numero_sinistre if sinistre else None,
        "documents": _documents_payload(db, sinistre),
        "notes": [
            {"id": n.id, "note": n.note, "author_name": n.author_name, "created_at": n.created_at.isoformat() if n.created_at else None}
            for n in notes
        ],
        "timeline": [
            {"id": e.id, "type": e.event_type, "label": e.label, "actor_name": e.actor_name, "created_at": e.created_at.isoformat() if e.created_at else None}
            for e in events
        ],
    }


@router.get("/{alerte_id}/etablissements-proches")
async def get_etablissements_proches(
    alerte_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Établissements de santé triés par distance depuis la position de l'alerte."""
    alerte = _require_alerte(db, alerte_id, current_user, LEVEL_CONSULTATION)
    hospitals = db.query(Hospital).filter(Hospital.est_actif == True).all()
    ranked = []
    for h in hospitals:
        dist = calculate_distance(alerte.latitude, alerte.longitude, h.latitude, h.longitude)
        # Estimation temps de trajet ~30 km/h en zone urbaine.
        eta = round(dist / 30 * 60)
        ranked.append({
            "id": h.id,
            "nom": h.nom,
            "adresse": h.adresse,
            "ville": h.ville,
            "telephone": h.telephone,
            "latitude": float(h.latitude) if h.latitude is not None else None,
            "longitude": float(h.longitude) if h.longitude is not None else None,
            "distance_km": round(dist, 1),
            "temps_min": max(eta, 1),
            "specialites": [s.strip() for s in (h.specialites or "").split(",") if s and s.strip()],
            "disponibilite": "Disponible" if h.est_actif else "Indisponible",
        })
    ranked.sort(key=lambda x: x["distance_km"])
    return ranked[: max(1, min(limit, 20))]


@router.get("/{alerte_id}/notes")
async def list_notes(alerte_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _require_alerte(db, alerte_id, current_user, LEVEL_CONSULTATION)
    notes = db.query(AlerteNote).filter(AlerteNote.alerte_id == alerte_id).order_by(AlerteNote.created_at.desc()).all()
    return [{"id": n.id, "note": n.note, "author_name": n.author_name, "created_at": n.created_at.isoformat() if n.created_at else None} for n in notes]


@router.post("/{alerte_id}/notes", status_code=status.HTTP_201_CREATED)
async def add_note(alerte_id: int, payload: NoteCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _require_alerte(db, alerte_id, current_user, LEVEL_EDITION)
    note = AlerteNote(
        alerte_id=alerte_id,
        author_id=current_user.id,
        author_name=getattr(current_user, "full_name", None) or getattr(current_user, "username", None),
        note=payload.note.strip(),
    )
    db.add(note)
    _log_event(db, alerte_id, "note", f"Note ajoutée par {note.author_name}", current_user)
    db.commit()
    db.refresh(note)
    return {"id": note.id, "note": note.note, "author_name": note.author_name, "created_at": note.created_at.isoformat()}


@router.put("/{alerte_id}/statut")
async def update_statut(alerte_id: int, payload: StatutUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    alerte = _require_alerte(db, alerte_id, current_user, LEVEL_EDITION)
    if payload.statut not in ALERTE_STATUTS:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs: {sorted(ALERTE_STATUTS)}")
    old = alerte.statut
    alerte.statut = payload.statut
    _log_event(db, alerte_id, "statut", f"Statut : {old} → {payload.statut}", current_user,
               {"old": old, "new": payload.statut, "commentaire": payload.commentaire})
    db.commit()
    return {"ok": True, "statut": payload.statut}


@router.put("/{alerte_id}/statut-medical")
async def update_statut_medical(alerte_id: int, payload: StatutMedicalUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _require_alerte(db, alerte_id, current_user, LEVEL_EDITION)
    sm = db.query(AlerteStatutMedical).filter(AlerteStatutMedical.alerte_id == alerte_id).first()
    if not sm:
        sm = AlerteStatutMedical(alerte_id=alerte_id)
        db.add(sm)
    for field in ("etat_patient", "motifs_symptomes", "besoins_immediats", "allergies_connues", "traitements_en_cours"):
        setattr(sm, field, getattr(payload, field))
    sm.updated_by_id = current_user.id
    sm.updated_by_name = getattr(current_user, "full_name", None) or getattr(current_user, "username", None)
    _log_event(db, alerte_id, "statut_medical", "Statut médical mis à jour", current_user)
    db.commit()
    db.refresh(sm)
    return {"ok": True, "updated_at": sm.updated_at.isoformat() if sm.updated_at else None}


@router.post("/{alerte_id}/transfer")
async def transfer_alerte(alerte_id: int, payload: TransferRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _require_alerte(db, alerte_id, current_user, LEVEL_EDITION)
    sinistre = _get_sinistre(db, alerte_id)
    if payload.cible == "affaires_medicales":
        target_label = "Affaires médicales"
        alerte.assigned_role = "affaires_medicales"
        alerte.assigned_at = datetime.utcnow()
        if sinistre:
            sinistre.medecin_referent_id = None
    elif payload.cible == "medecin_conseil":
        target_label = "Médecin-conseil"
        alerte.assigned_role = "medecin_conseil"
        alerte.assigned_at = datetime.utcnow()
    elif payload.cible.startswith("user:"):
        user_id = int(payload.cible.split(":", 1)[1])
        target = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not target:
            raise HTTPException(status_code=404, detail="Utilisateur cible introuvable")
        target_label = target.full_name or target.username
        target_role = getattr(target, "role", None)
        if hasattr(target_role, "value"):
            target_role = target_role.value
        alerte.assigned_role = "medecin_conseil" if str(target_role) == "medecin_referent_mh" else "affaires_medicales"
        alerte.assigned_at = datetime.utcnow()
        if sinistre:
            sinistre.medecin_referent_id = target.id
    else:
        raise HTTPException(status_code=400, detail="Cible invalide")
    _log_event(db, alerte_id, "transfert", f"Alerte transférée vers {target_label}", current_user,
               {"cible": payload.cible, "commentaire": payload.commentaire})
    db.commit()
    return {"ok": True, "cible": target_label}


@router.post("/{alerte_id}/prevenir-hopital")
async def prevenir_hopital(alerte_id: int, payload: NotifyHospitalRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Notifier l'établissement sélectionné de l'arrivée du patient."""
    alerte = _require_alerte(db, alerte_id, current_user, LEVEL_EDITION)
    hospital = db.query(Hospital).filter(Hospital.id == payload.hospital_id, Hospital.est_actif == True).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Établissement introuvable")
    sinistre = _get_sinistre(db, alerte_id)
    if not sinistre:
        # L'orientation crée le dossier sinistre si le centre n'en a pas encore.
        sinistre = Sinistre(
            alerte_id=alerte.id,
            souscription_id=alerte.souscription_id,
            hospital_id=hospital.id,
            numero_sinistre=generate_numero_sinistre(),
            statut="en_cours",
        )
        db.add(sinistre)
        db.flush()
        _log_event(db, alerte_id, "orientation", f"Sinistre {sinistre.numero_sinistre} ouvert, orientation vers {hospital.nom}", current_user)
    elif not sinistre.hospital_id:
        sinistre.hospital_id = hospital.id
        _log_event(db, alerte_id, "orientation", f"Orientation vers {hospital.nom}", current_user)
    await notify_hospital_reception(
        db=db,
        sinistre=sinistre,
        alerte=alerte,
        hospital=hospital,
        souscription=None,
        assure=alerte.user,
    )
    _log_event(db, alerte_id, "notification_hopital", f"Hôpital prévenu : {hospital.nom}", current_user)
    db.commit()
    return {"ok": True, "hospital": hospital.nom}


@router.post("/{alerte_id}/action")
async def execute_action(alerte_id: int, payload: ActionRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Actions du bandeau : ambulance, prise en charge directe (BPCU), hôtel."""
    alerte = _require_alerte(db, alerte_id, current_user, LEVEL_EDITION)
    sinistre = _get_sinistre(db, alerte_id)

    if payload.action == "ambulance":
        if not sinistre:
            raise HTTPException(status_code=400, detail="Orientez d'abord l'alerte vers un établissement")
        from app.services.sinistre_workflow_service import update_workflow_step
        update_workflow_step(db, sinistre, alerte, "ambulance_en_route", "in_progress",
                             actor_id=current_user.id, notes=payload.notes)
        _log_event(db, alerte_id, "ambulance", "Envoi d'ambulance demandé", current_user)
        label = "Ambulance en route"

    elif payload.action == "prise_en_charge":
        if not sinistre:
            raise HTTPException(status_code=400, detail="Orientez d'abord l'alerte vers un établissement")
        from app.services.mhc_care_document_service import issue_care_document, CareDocumentPermissionError
        try:
            docs = issue_care_document(db, sinistre, "BPCU", current_user, notes=payload.notes, alerte=alerte)
        except CareDocumentPermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        label = f"Prise en charge {docs[0].numero if docs else ''} émise".strip()
        _log_event(db, alerte_id, "prise_en_charge", label, current_user)

    elif payload.action == "hotel":
        _log_event(db, alerte_id, "hotel", "Demande d'hébergement enregistrée", current_user, {"notes": payload.notes})
        label = "Demande d'hôtel enregistrée"

    else:
        raise HTTPException(status_code=400, detail="Action inconnue")

    if alerte.statut == "en_attente":
        alerte.statut = "en_cours"
    db.commit()
    return {"ok": True, "label": label}


@router.get("/{alerte_id}/timeline")
async def get_timeline(alerte_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    alerte = _require_alerte(db, alerte_id, current_user, LEVEL_CONSULTATION)
    sinistre = _get_sinistre(db, alerte_id)
    events = db.query(AlerteEvent).filter(AlerteEvent.alerte_id == alerte_id).order_by(AlerteEvent.created_at.asc()).all()
    return {
        "etape_courante": _current_step(db, alerte, sinistre),
        "events": [
            {"id": e.id, "type": e.event_type, "label": e.label, "actor_name": e.actor_name, "created_at": e.created_at.isoformat() if e.created_at else None}
            for e in events
        ],
    }
