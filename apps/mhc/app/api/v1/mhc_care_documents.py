from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import Role
from app.core.http_headers import content_disposition
from app.core.mhc_nomenclature import DOCUMENT_TITLES, MhcCareDocumentType, document_catalog
from app.core.mhc_tarif_reference import projet_tarif_public, split_prime_nette
from app.api.v1.auth import get_current_user
from app.models.alerte import Alerte
from app.models.hospital import Hospital
from app.models.mhc_care_document import MhcCareDocument
from app.models.sinistre import Sinistre
from app.models.notification import Notification
from app.models.user import User
from app.schemas.mhc_care_document import (
    MhcCareDocumentIssueRequest,
    MhcCareDocumentListResponse,
    MhcCareDocumentResponse,
    MhcCareDocumentValidationRequest,
)
from app.services.mhc_care_document_pdf import build_care_document_pdf
from app.services.mhc_care_document_service import (
    CareDocumentPermissionError,
    GROUP_LABELS,
    VALIDATION_PENDING,
    allowed_next_actions,
    get_care_document,
    invalidate_bpcu_for_reorientation,
    issue_care_document,
    list_care_documents,
    load_sinistre_for_care,
    required_validator_groups,
    validate_care_document,
)

router = APIRouter()

CARE_ROLES = {
    Role.ADMIN,
    Role.MEDECIN_REFERENT_MH,
    Role.MEDICAL_REVIEWER,
    Role.AGENT_SINISTRE_MH,
    Role.SOS_OPERATOR,
    Role.MEDECIN_HOPITAL,
    Role.DOCTOR,
    Role.HOSPITAL_ADMIN,
    Role.AGENT_RECEPTION_HOPITAL,
    # Affaires médicales MHC : 2e validation des demandes, demande de
    # rapatriement funéraire, attestations 121/122, réorientation.
    Role.AGENT_MEDICAL_MHC,
    Role.SUPERVISEUR_AFFAIRES_MEDICALES,
    Role.AGENT_CONFORMITE_MEDICAL,
}


def _ensure_role(user: User) -> None:
    if user.role not in CARE_ROLES and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé au pôle médical / sinistre MHC.")


def _to_response(doc) -> MhcCareDocumentResponse:
    doc_type = MhcCareDocumentType(doc.document_type)
    titre = DOCUMENT_TITLES.get(doc_type, doc.document_type)
    validation_status = getattr(doc, "validation_status", None) or "non_requise"
    validations_requises: List[str] = []
    if validation_status == VALIDATION_PENDING:
        approuves = {v.get("groupe") for v in (doc.validations or []) if v.get("approuve")}
        validations_requises = [
            GROUP_LABELS[g] for g in required_validator_groups(doc_type) if g not in approuves
        ]
    return MhcCareDocumentResponse(
        id=doc.id,
        sinistre_id=doc.sinistre_id,
        document_type=doc.document_type,
        titre=titre,
        numero=doc.numero,
        statut=doc.statut,
        issued_at=doc.issued_at,
        valid_until=doc.valid_until,
        issued_by_id=doc.issued_by_id,
        parent_document_id=doc.parent_document_id,
        payload=doc.payload,
        notes=doc.notes,
        validation_status=validation_status,
        validated_at=getattr(doc, "validated_at", None),
        validations=getattr(doc, "validations", None),
        validations_requises=validations_requises,
    )


@router.get("/referentiel")
async def get_mhc_referentiel(current_user: User = Depends(get_current_user)):
    """Catalogue documentaire, codes opération et grilles du projet de tarif MHC."""
    from decimal import Decimal

    from app.core.mhc_nomenclature import MHC_COUNTRY_CODES, OPERATION_LABELS

    def _dec(obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, dict):
            return {k: _dec(v) for k, v in obj.items()}
        return obj

    return {
        "documents": document_catalog(),
        "codes_operation": OPERATION_LABELS,
        "codes_pays": [{"code": code, "pays": nom} for code, nom in sorted(MHC_COUNTRY_CODES.items())],
        "projet_tarif": projet_tarif_public(),
        "repartition_exemple": {
            "assureur_20": _dec(split_prime_nette(Decimal("6500"), Decimal("20"))),
            "assureur_0": _dec(split_prime_nette(Decimal("6500"), Decimal("0"))),
        },
    }



class CareDocumentTraceItem(BaseModel):
    id: int
    document_type: str
    titre: str
    numero: str
    statut: str
    validation_status: str
    issued_at: object = None
    sinistre_id: int = None
    numero_sinistre: Optional[str] = None
    alerte_id: Optional[int] = None
    assure_id: Optional[int] = None
    assure_nom: Optional[str] = None
    hospital_nom: Optional[str] = None


@router.get("/care-documents", response_model=List[CareDocumentTraceItem])
async def list_all_care_documents(
    q: Optional[str] = None,
    document_type: Optional[str] = None,
    statut: Optional[str] = None,
    limit: int = 300,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Traçabilité de tous les documents de prise en charge émis.

    Recherche libre sur l'assuré, le numéro de document ou de sinistre.
    Les profils hospitaliers ne voient que les documents de leurs établissements.
    """
    _ensure_role(current_user)

    query = (
        db.query(MhcCareDocument, Sinistre, Alerte, User, Hospital)
        .join(Sinistre, MhcCareDocument.sinistre_id == Sinistre.id)
        .outerjoin(Alerte, Sinistre.alerte_id == Alerte.id)
        .outerjoin(User, Alerte.user_id == User.id)
        .outerjoin(Hospital, Sinistre.hospital_id == Hospital.id)
    )

    # Portée hospitalière : réception, médecins et admin d'établissement.
    hospital_roles = {Role.MEDECIN_HOPITAL, Role.HOSPITAL_ADMIN, Role.AGENT_RECEPTION_HOPITAL, Role.DOCTOR}
    if current_user.role in hospital_roles and getattr(current_user, "hospital_id", None):
        query = query.filter(Sinistre.hospital_id == current_user.hospital_id)

    if document_type:
        query = query.filter(MhcCareDocument.document_type == document_type)
    if statut:
        query = query.filter(MhcCareDocument.statut == statut)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            (User.full_name.ilike(term))
            | (MhcCareDocument.numero.ilike(term))
            | (Sinistre.numero_sinistre.ilike(term))
        )

    rows = (
        query.order_by(MhcCareDocument.issued_at.desc())
        .limit(min(limit, 500))
        .all()
    )

    items = []
    for doc, sinistre, alerte, assure, hospital in rows:
        doc_type = MhcCareDocumentType(doc.document_type)
        items.append(
            CareDocumentTraceItem(
                id=doc.id,
                document_type=doc.document_type,
                titre=DOCUMENT_TITLES.get(doc_type, doc.document_type),
                numero=doc.numero,
                statut=doc.statut,
                validation_status=getattr(doc, "validation_status", None) or "non_requise",
                issued_at=doc.issued_at.isoformat() if doc.issued_at else None,
                sinistre_id=sinistre.id,
                numero_sinistre=sinistre.numero_sinistre,
                alerte_id=alerte.id if alerte else None,
                assure_id=assure.id if assure else None,
                assure_nom=(assure.full_name or assure.email) if assure else None,
                hospital_nom=hospital.nom if hospital else None,
            )
        )
    return items


@router.get("/sinistres/{sinistre_id}/care-documents", response_model=MhcCareDocumentListResponse)
async def get_sinistre_care_documents(
    sinistre_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_role(current_user)
    sinistre = load_sinistre_for_care(db, sinistre_id)
    if not sinistre:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sinistre introuvable.")
    docs = list_care_documents(db, sinistre_id)
    actions = allowed_next_actions(sinistre)
    return MhcCareDocumentListResponse(
        sinistre_id=sinistre.id,
        numero_sinistre=sinistre.numero_sinistre,
        dossier_ouvert=bool(actions),
        actions_possibles=actions,
        documents=[_to_response(d) for d in docs],
    )


@router.post(
    "/sinistres/{sinistre_id}/care-documents",
    response_model=List[MhcCareDocumentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_sinistre_care_document(
    sinistre_id: int,
    body: MhcCareDocumentIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_role(current_user)
    sinistre = load_sinistre_for_care(db, sinistre_id)
    if not sinistre:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sinistre introuvable.")
    try:
        created = issue_care_document(
            db,
            sinistre,
            body.document_type,
            current_user,
            payload=body.payload,
            notes=body.notes,
            alerte=sinistre.alerte,
        )
    except CareDocumentPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    for doc in created:
        db.refresh(doc)
    return [_to_response(d) for d in created]


@router.post(
    "/care-documents/{document_id}/validation",
    response_model=MhcCareDocumentResponse,
)
async def validate_care_document_endpoint(
    document_id: int,
    body: MhcCareDocumentValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Valider (ou refuser) un bon en attente de validation.

    Selon le référentiel : BRPCU/BRF → Pôle médical MHC ; BH/BPH → Médecin-conseil
    + Pôle médical MHC ; BRS → Pôle médical MHC + Partenaire-Santé (double validation).
    """
    _ensure_role(current_user)
    document = get_care_document(db, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")
    sinistre = load_sinistre_for_care(db, document.sinistre_id)
    if not sinistre:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sinistre introuvable.")
    try:
        validate_care_document(
            db,
            sinistre,
            document,
            current_user,
            approve=body.approve,
            notes=body.notes,
            alerte=sinistre.alerte,
        )
    except CareDocumentPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(document)
    return _to_response(document)


REORIENTATION_ROLES = {
    Role.ADMIN,
    Role.MEDECIN_REFERENT_MH,
    Role.AGENT_MEDICAL_MHC,
    Role.SUPERVISEUR_AFFAIRES_MEDICALES,
}


class ReorientationRequest(BaseModel):
    hospital_id: int
    notes: Optional[str] = None


@router.post("/sinistres/{sinistre_id}/reorientation")
async def reorient_sinistre(
    sinistre_id: int,
    body: ReorientationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Réorientation (étape 4) : médecin-conseil / affaires médicales MHC.

    Change la clinique et remet l'acceptation à zéro : le bon 111 émis pour
    l'ancienne clinique est expiré — la nouvelle clinique devra accepter le
    patient et émettre un nouveau bon 111 (l'accord du médecin-conseil reste).
    """
    if current_user.role not in REORIENTATION_ROLES and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé au médecin-conseil ou aux affaires médicales MHC.")

    sinistre = load_sinistre_for_care(db, sinistre_id)
    if not sinistre:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sinistre introuvable.")
    if sinistre.statut in {"resolu", "annule"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le dossier est clos.")
    if body.hospital_id == sinistre.hospital_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le dossier est déjà rattaché à cet établissement.")

    # Réorientation impossible une fois l'hospitalisation en cours (bon 113 effectif).
    effective_docs = [d for d in (sinistre.care_documents or []) if (d.statut or "emi") == "emi"]
    if any(d.document_type in {"bh", "bph"} for d in effective_docs):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Réorientation impossible : une hospitalisation est en cours.")

    hospital = db.query(Hospital).filter(Hospital.id == body.hospital_id, Hospital.est_actif == True).first()
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Établissement introuvable.")

    from app.core.mhc_nomenclature import MhcCareDocumentStatus, MhcCareDocumentType
    from datetime import datetime

    old_hospital = sinistre.hospital
    old_bpcu = None
    for d in effective_docs:
        if d.document_type == MhcCareDocumentType.BPCU.value:
            invalidate_bpcu_for_reorientation(d)
            old_bpcu = d

    sinistre.hospital_id = hospital.id
    stay = sinistre.hospital_stay
    if stay is not None:
        stay.hospital_id = hospital.id

    # Notifier l'agent d'accueil et l'agent médical de la nouvelle clinique.
    recipients = (
        db.query(User)
        .filter(
            User.role.in_([Role.AGENT_RECEPTION_HOPITAL, Role.MEDECIN_HOPITAL]),
            User.is_active == True,  # noqa: E712
            User.hospital_id == hospital.id,
        )
        .all()
    )
    sinistre_label = sinistre.numero_sinistre or f"sinistre #{sinistre.id}"
    origin = f" depuis « {old_hospital.nom} »" if old_hospital else ""
    for u in recipients:
        db.add(Notification(
            user_id=u.id,
            type_notification="sinistre_reorientation",
            titre="Patient réorienté vers votre établissement",
            message=f"Le dossier {sinistre_label} a été réorienté{origin}. Veuillez accepter le patient et émettre le bon 111.",
            lien_relation_id=sinistre.id,
            lien_relation_type="sinistre",
        ))

    db.commit()
    return {
        "ok": True,
        "hospital_id": hospital.id,
        "hospital": hospital.nom,
        "bpcu_invalide": old_bpcu.numero if old_bpcu else None,
    }


@router.get("/care-documents/{document_id}/pdf")
async def download_care_document_pdf(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_role(current_user)
    document = get_care_document(db, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")
    pdf_bytes = build_care_document_pdf(document)
    filename = f"{document.document_type}-{document.numero}.pdf".replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition("inline", filename)},
    )
