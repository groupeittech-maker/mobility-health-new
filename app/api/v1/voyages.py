from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import re
import unicodedata
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.projet_voyage import ProjetVoyage
from app.models.projet_voyage_document import ProjetVoyageDocument
from app.schemas.projet_voyage import (
    ProjetVoyageBase,
    ProjetVoyageCreate,
    ProjetVoyageResponse,
    ProjetVoyageDocumentResponse,
    ProjetVoyageUpdate,
)
from app.services.minio_service import MinioService

router = APIRouter()

logger = logging.getLogger(__name__)

MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 Mo
ALLOWED_DOCUMENT_TYPES = {
    "passport",
    "id_card",
    "residence_permit",
    "travel_booking",
    "photo_identity",  # Photo d'identité pour l'e-carte
    "other",
}


@router.get("/", response_model=List[ProjetVoyageResponse])
async def list_projets_voyage(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lister les projets de voyage de l'utilisateur connecté"""
    query = db.query(ProjetVoyage).filter(ProjetVoyage.user_id == current_user.id)
    
    # Si l'utilisateur est admin, il peut voir tous les projets
    if current_user.role.value == "admin":
        query = db.query(ProjetVoyage)
    
    projets = query.order_by(ProjetVoyage.created_at.desc()).offset(skip).limit(limit).all()
    
    return [ProjetVoyageResponse.model_validate(projet) for projet in projets]


# Autoriser également l'URL sans slash final (/voyages) pour GET afin d'éviter les redirections 307 côté client.
router.add_api_route(
    "",
    list_projets_voyage,
    methods=["GET"],
    include_in_schema=False,
)


def _normalize_country_name(name: str) -> str:
    """Normalise un nom de pays (enlever accents, espaces, minuscules)"""
    if not name:
        return ""
    # Supprimer les accents
    normalized = unicodedata.normalize('NFD', name.lower())
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    # Supprimer les espaces
    normalized = re.sub(r'\s+', '', normalized)
    return normalized.strip()


def _extract_countries_from_notes(notes: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Extrait le pays de résidence et le pays de destination depuis les notes"""
    residence_country = None
    destination_country = None
    
    if not notes:
        return residence_country, destination_country
    
    # Chercher "Pays de résidence: ..."
    residence_match = re.search(r'Pays de résidence:\s*([^\n]+)', notes, re.IGNORECASE)
    if residence_match:
        residence_country = residence_match.group(1).strip()
    
    # Chercher "Pays de destination: ..."
    destination_match = re.search(r'Pays de destination:\s*([^\n]+)', notes, re.IGNORECASE)
    if destination_match:
        destination_country = destination_match.group(1).strip()
    
    return residence_country, destination_country


@router.post("/", response_model=ProjetVoyageResponse, status_code=status.HTTP_201_CREATED)
async def create_projet_voyage(
    projet_data: ProjetVoyageBase,  # Utiliser ProjetVoyageBase au lieu de ProjetVoyageCreate
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouveau projet de voyage"""
    logger.info(f"Création d'un projet de voyage pour l'utilisateur {current_user.id}")
    logger.debug(f"Données reçues: {projet_data.model_dump()}")
    
    # Utiliser automatiquement l'ID de l'utilisateur connecté
    # Vérifier que la date de retour est après la date de départ
    if projet_data.date_retour and projet_data.date_retour <= projet_data.date_depart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La date de retour doit être postérieure à la date de départ"
        )
    
    # Vérifier que le pays de destination est différent du pays de résidence
    residence_country, destination_country = _extract_countries_from_notes(projet_data.notes)
    if residence_country and destination_country:
        normalized_residence = _normalize_country_name(residence_country)
        normalized_destination = _normalize_country_name(destination_country)
        if normalized_residence and normalized_destination and normalized_residence == normalized_destination:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le pays de destination doit être différent du pays de résidence"
            )
    
    # Créer le projet avec l'ID de l'utilisateur connecté
    projet_data_dict = projet_data.model_dump()
    projet_data_dict['user_id'] = current_user.id
    projet = ProjetVoyage(**projet_data_dict)
    db.add(projet)
    db.commit()
    db.refresh(projet)
    
    response = ProjetVoyageResponse.model_validate(projet)
    response.documents = []
    return response


# Autoriser également l'URL sans slash final (/voyages) afin d'éviter les redirections 307 côté client.
router.add_api_route(
    "",
    create_projet_voyage,
    methods=["POST"],
    include_in_schema=False,
)


@router.get("/{projet_id}", response_model=ProjetVoyageResponse)
async def get_projet_voyage(
    projet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir un projet de voyage par ID"""
    projet = _get_project_or_404(
        db,
        projet_id,
        current_user,
        include_documents=True,
    )
    response = ProjetVoyageResponse.model_validate(projet)
    response.documents = [_serialize_document(doc) for doc in sorted(
        projet.documents,
        key=lambda d: d.created_at,
        reverse=True,
    )]
    return response


@router.put("/{projet_id}", response_model=ProjetVoyageResponse)
async def update_projet_voyage(
    projet_id: int,
    projet_data: ProjetVoyageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour un projet de voyage"""
    projet = _get_project_or_404(
        db,
        projet_id,
        current_user,
        include_documents=False,
    )
    
    # Vérifier que la date de retour est après la date de départ si les deux sont fournies
    date_depart = projet_data.date_depart if projet_data.date_depart is not None else projet.date_depart
    date_retour = projet_data.date_retour if projet_data.date_retour is not None else projet.date_retour
    
    if date_retour and date_retour <= date_depart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La date de retour doit être postérieure à la date de départ"
        )
    
    # Mettre à jour uniquement les champs fournis
    update_data = projet_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(projet, field, value)
    
    db.commit()
    db.refresh(projet)
    
    # Recharger avec les documents
    projet = _get_project_or_404(
        db,
        projet_id,
        current_user,
        include_documents=True,
    )
    
    response = ProjetVoyageResponse.model_validate(projet)
    response.documents = [_serialize_document(doc) for doc in sorted(
        projet.documents,
        key=lambda d: d.created_at,
        reverse=True,
    )]
    
    return response


@router.delete("/{projet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_projet_voyage(
    projet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Supprimer un projet de voyage"""
    projet = _get_project_or_404(
        db,
        projet_id,
        current_user,
        include_documents=False,
    )
    
    # Vérifier qu'aucune souscription n'est liée à ce projet
    from app.models.souscription import Souscription
    souscriptions = db.query(Souscription).filter(
        Souscription.projet_voyage_id == projet_id
    ).all()
    
    if souscriptions:
        # Vérifier s'il y a des souscriptions avec paiement effectué
        from app.core.enums import StatutSouscription
        souscriptions_payees = [
            s for s in souscriptions 
            if s.statut.value in ['active', 'expiree', 'suspendue', 'resiliee']
        ]
        
        if souscriptions_payees:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de supprimer ce projet : il est lié à une ou plusieurs souscriptions actives ou terminées"
            )
    
    # Supprimer le projet (les documents seront supprimés automatiquement via cascade)
    db.delete(projet)
    db.commit()
    
    return None


@router.get(
    "/{projet_id}/documents",
    response_model=List[ProjetVoyageDocumentResponse],
)
async def list_project_documents(
    projet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projet = _get_project_or_404(
        db,
        projet_id,
        current_user,
        include_documents=True,
    )
    return [
        _serialize_document(doc)
        for doc in sorted(
            projet.documents,
            key=lambda d: d.created_at,
            reverse=True,
        )
    ]


@router.post(
    "/{projet_id}/documents",
    response_model=ProjetVoyageDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_project_document(
    projet_id: int,
    doc_type: str = Form(..., description="passport, id_card, residence_permit, travel_booking, other"),
    display_name: Optional[str] = Form(None, description="Libellé personnalisé"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_type = doc_type.lower()
    if doc_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type de document invalide ({doc_type}).",
        )

    projet = _get_project_or_404(
        db,
        projet_id,
        current_user,
        include_documents=False,
    )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier envoyé est vide.",
        )
    if len(file_bytes) > MAX_DOCUMENT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fichier trop volumineux (10 Mo max).",
        )

    original_name = file.filename or "document"
    sanitized_name = _sanitize_filename(original_name)
    object_name = f"projects/{projet.id}/{uuid.uuid4().hex}_{sanitized_name}"
    content_type = file.content_type or "application/octet-stream"

    minio_service = MinioService()
    MinioService.ensure_project_documents_bucket()
    minio_service.upload_file(
        MinioService.BUCKET_PROJECT_DOCUMENTS,
        object_name,
        file_bytes,
        content_type=content_type,
    )

    document = ProjetVoyageDocument(
        projet_voyage_id=projet.id,
        doc_type=doc_type,
        display_name=display_name.strip() if display_name else original_name,
        bucket_name=MinioService.BUCKET_PROJECT_DOCUMENTS,
        object_name=object_name,
        content_type=content_type,
        file_size=len(file_bytes),
        uploaded_by=current_user.id,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return _serialize_document(document)


def _get_project_or_404(
    db: Session,
    projet_id: int,
    current_user: User,
    include_documents: bool = False,
) -> ProjetVoyage:
    query = db.query(ProjetVoyage)
    if include_documents:
        query = query.options(selectinload(ProjetVoyage.documents))
    projet = query.filter(ProjetVoyage.id == projet_id).first()
    if not projet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet de voyage non trouvé",
        )
    if projet.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas accès à ce projet",
        )
    return projet


def _serialize_document(document: ProjetVoyageDocument) -> ProjetVoyageDocumentResponse:
    download_url: Optional[str] = None
    try:
        download_url = MinioService.generate_signed_url(
            document.bucket_name,
            document.object_name,
            expires=timedelta(minutes=30),
        )
    except Exception as error:
        logger.warning("Impossible de générer l'URL signée pour le document %s: %s", document.id, error)
    return ProjetVoyageDocumentResponse(
        id=document.id,
        doc_type=document.doc_type,
        display_name=document.display_name,
        content_type=document.content_type,
        file_size=document.file_size,
        uploaded_by=document.uploaded_by,
        uploaded_at=document.uploaded_at,
        download_url=download_url,
    )


def _sanitize_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKD", filename)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9.\-]+", "_", ascii_name)
    cleaned = cleaned.strip("._")
    return cleaned[:150] or "document"
