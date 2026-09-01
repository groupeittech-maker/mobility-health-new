from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import Role
from app.core.mhc_nomenclature import DOCUMENT_TITLES, MhcCareDocumentType, document_catalog
from app.core.mhc_tarif_reference import projet_tarif_public, split_prime_nette
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.mhc_care_document import (
    MhcCareDocumentIssueRequest,
    MhcCareDocumentListResponse,
    MhcCareDocumentResponse,
)
from app.services.mhc_care_document_pdf import build_care_document_pdf
from app.services.mhc_care_document_service import (
    allowed_next_actions,
    get_care_document,
    issue_care_document,
    list_care_documents,
    load_sinistre_for_care,
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
}


def _ensure_role(user: User) -> None:
    if user.role not in CARE_ROLES and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé au pôle médical / sinistre MHC.")


def _to_response(doc) -> MhcCareDocumentResponse:
    titre = DOCUMENT_TITLES.get(MhcCareDocumentType(doc.document_type), doc.document_type)
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
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    for doc in created:
        db.refresh(doc)
    return [_to_response(d) for d in created]


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
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
