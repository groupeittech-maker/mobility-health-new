from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import re
import unicodedata
import logging
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user, get_current_user_optional
from app.models.destination import DestinationCountry
from app.models.user import User
from app.models.projet_voyage import ProjetVoyage
from app.models.projet_voyage_document import ProjetVoyageDocument
from app.models.souscription import Souscription
from app.schemas.projet_voyage import (
    ProjetVoyageBase,
    ProjetVoyageCreate,
    ProjetVoyageResponse,
    ProjetVoyageDocumentResponse,
    ProjetVoyageUpdate,
)
from app.services.minio_service import MinioService
from app.services.project_document_storage import (
    LOCAL_PROJECT_DOCUMENTS_BUCKET,
    write_local_project_file,
)
from app.core.enums import StatutProjetVoyage, QuestionnaireType, Role, Role
from app.core.security import decode_download_access_token

router = APIRouter()

# Mapping nom enum -> valeur DB (PostgreSQL attend les valeurs en minuscules)
_STATUT_VALUES = {e.name: e.value for e in StatutProjetVoyage}
_QUESTIONNAIRE_VALUES = {e.name: e.value for e in QuestionnaireType}

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
    
    return [_serialize_project_response(db, projet) for projet in projets]


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


def _extract_destination_city_from_notes(notes: Optional[str]) -> Optional[str]:
    """Extrait la ville de destination depuis les notes si elle existe."""
    if not notes:
        return None
    destination_match = re.search(r'Ville de destination:\s*([^\n]+)', notes, re.IGNORECASE)
    if destination_match:
        return destination_match.group(1).strip()
    return None


def _build_destination_display(city: Optional[str], country: Optional[str]) -> Optional[str]:
    city = (city or "").strip()
    country = (country or "").strip()
    if city and country:
        return f"{city}, {country}"
    return city or country or None


def _get_destination_country_name(
    db: Session,
    destination_country_id: Optional[int],
    notes: Optional[str],
) -> Optional[str]:
    _, destination_country_from_notes = _extract_countries_from_notes(notes)
    if destination_country_from_notes:
        return destination_country_from_notes
    if destination_country_id:
        destination_country = db.query(DestinationCountry).filter(
            DestinationCountry.id == destination_country_id
        ).first()
        if destination_country:
            return destination_country.nom
    return None


def _validate_destination_country(
    db: Session,
    current_user: User,
    destination_country_id: Optional[int],
    notes: Optional[str],
) -> None:
    residence_country, _ = _extract_countries_from_notes(notes)
    residence_country = (current_user.pays_residence or residence_country or "").strip()
    destination_country = (_get_destination_country_name(db, destination_country_id, notes) or "").strip()
    if not residence_country:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veuillez renseigner votre pays de résidence dans votre profil avant de souscrire"
        )
    destination_country_code = ""
    if destination_country_id:
        destination_country_row = db.query(DestinationCountry).filter(
            DestinationCountry.id == destination_country_id
        ).first()
        if destination_country_row and destination_country_row.code:
            destination_country_code = destination_country_row.code.strip()
    normalized_residence = _normalize_country_name(residence_country)
    normalized_destination = _normalize_country_name(destination_country)
    normalized_destination_code = _normalize_country_name(destination_country_code)
    if normalized_residence and (
        normalized_residence == normalized_destination
        or (normalized_destination_code and normalized_residence == normalized_destination_code)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le pays de destination doit être différent du pays de résidence"
        )


def _serialize_project_response(
    db: Session,
    projet: ProjetVoyage,
    documents: Optional[list[ProjetVoyageDocumentResponse]] = None,
) -> ProjetVoyageResponse:
    response = ProjetVoyageResponse.model_validate(projet)
    _, destination_country_from_notes = _extract_countries_from_notes(projet.notes)
    destination_city_from_notes = _extract_destination_city_from_notes(projet.notes)

    destination_country_name = destination_country_from_notes
    if not destination_country_name and getattr(projet, "destination_country_id", None):
        destination_country = db.query(DestinationCountry).filter(
            DestinationCountry.id == projet.destination_country_id
        ).first()
        destination_country_name = destination_country.nom if destination_country else None

    destination_city_name = destination_city_from_notes or projet.destination
    response.destination_country_name = destination_country_name
    response.destination_display = _build_destination_display(
        destination_city_name,
        destination_country_name,
    )
    response.documents = documents or []
    return response


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
    
    _validate_destination_country(
        db,
        current_user,
        projet_data.destination_country_id,
        projet_data.notes,
    )
    
    # Créer le projet avec l'ID de l'utilisateur connecté
    projet_data_dict = projet_data.model_dump()
    projet_data_dict['user_id'] = current_user.id
    # PostgreSQL n'accepte que les valeurs enum en minuscules (en_planification), pas le nom (EN_PLANIFICATION)
    statut_raw = projet_data_dict.get('statut')
    if hasattr(statut_raw, 'value'):
        statut_db = statut_raw.value
    elif isinstance(statut_raw, str) and statut_raw.upper() in _STATUT_VALUES:
        statut_db = _STATUT_VALUES[statut_raw.upper()]
    else:
        statut_db = StatutProjetVoyage.EN_PLANIFICATION.value
    qtype_raw = projet_data_dict.get('questionnaire_type')
    if hasattr(qtype_raw, 'value'):
        qtype_db = qtype_raw.value
    elif isinstance(qtype_raw, str) and qtype_raw.upper() in _QUESTIONNAIRE_VALUES:
        qtype_db = _QUESTIONNAIRE_VALUES[qtype_raw.upper()]
    else:
        qtype_db = QuestionnaireType.LONG.value
    # Ne pas passer statut/questionnaire_type au constructeur pour éviter que SQLAlchemy n'envoie le nom
    projet_data_dict.pop('statut', None)
    projet_data_dict.pop('questionnaire_type', None)
    projet = ProjetVoyage(**projet_data_dict)
    projet.statut = statut_db
    projet.questionnaire_type = qtype_db
    logger.info("Création projet: statut=%s questionnaire_type=%s (valeurs DB)", statut_db, qtype_db)
    db.add(projet)
    db.commit()
    db.refresh(projet)
    
    return _serialize_project_response(db, projet)


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
    documents = [_serialize_document(doc) for doc in sorted(
        projet.documents,
        key=lambda d: d.created_at,
        reverse=True,
    )]
    return _serialize_project_response(db, projet, documents=documents)


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

    destination_country_id = (
        projet_data.destination_country_id
        if projet_data.destination_country_id is not None
        else projet.destination_country_id
    )
    notes = projet_data.notes if projet_data.notes is not None else projet.notes
    _validate_destination_country(
        db,
        current_user,
        destination_country_id,
        notes,
    )
    
    # Mettre à jour uniquement les champs fournis
    update_data = projet_data.model_dump(exclude_unset=True)
    # PostgreSQL attend les valeurs d'enum en minuscules
    if 'statut' in update_data:
        s = update_data['statut']
        if hasattr(s, 'value'):
            update_data['statut'] = s.value
        elif isinstance(s, str) and s.upper() in _STATUT_VALUES:
            update_data['statut'] = _STATUT_VALUES[s.upper()]
    if 'questionnaire_type' in update_data:
        q = update_data['questionnaire_type']
        if hasattr(q, 'value'):
            update_data['questionnaire_type'] = q.value
        elif isinstance(q, str) and q.upper() in _QUESTIONNAIRE_VALUES:
            update_data['questionnaire_type'] = _QUESTIONNAIRE_VALUES[q.upper()]
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
    
    documents = [_serialize_document(doc) for doc in sorted(
        projet.documents,
        key=lambda d: d.created_at,
        reverse=True,
    )]
    
    return _serialize_project_response(db, projet, documents=documents)


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


def _is_internal_minio_url(url: Optional[str]) -> bool:
    if not url:
        return False
    u = (url or "").lower()
    return "minio:" in u or "localhost:9000" in u or "127.0.0.1:9000" in u


def _build_document_proxy_url(document_id: int) -> str:
    """URL de proxy pour télécharger un document projet (contourne minio:9000)."""
    base = (getattr(settings, "API_PUBLIC_BASE_URL", None) or "").strip().rstrip("/")
    if not base:
        return ""
    return f"{base}/api/v1/voyages/documents/{document_id}/download"


@router.get(
    "/documents/{document_id}/download",
    response_class=StreamingResponse,
)
async def download_project_document(
    document_id: int,
    token: Optional[str] = Query(None, description="JWT court pour accès direct au document projet"),
    disposition: str = Query("attachment", description="attachment ou inline"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Télécharge une pièce jointe du projet (stream API : MinIO ou fichier local selon l’enregistrement)."""
    doc = db.query(ProjetVoyageDocument).filter(ProjetVoyageDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document non trouvé")
    projet = db.query(ProjetVoyage).filter(ProjetVoyage.id == doc.projet_voyage_id).first()
    if not projet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet non trouvé")
    # Accès : token direct valide OU utilisateur connecté (propriétaire, admin, production)
    if token:
        doc_id = decode_download_access_token(token, "project_document")
        if doc_id is None or doc_id != document_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token document invalide ou expiré")
    else:
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")
        is_owner = projet.user_id == current_user.id
        is_admin_or_production = current_user.role in (Role.ADMIN, Role.PRODUCTION_AGENT)
        if not is_owner and not is_admin_or_production:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à ce document")
    from app.services.project_document_storage import read_project_document_bytes

    data = read_project_document_bytes(doc.bucket_name, doc.object_name)
    if not data:
        logger.warning(
            "Impossible de lire le document %s (bucket=%s, key=%s)",
            document_id,
            doc.bucket_name,
            doc.object_name,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable dans le stockage",
        )
    filename = doc.display_name or f"document-{doc.id}"
    media_type = doc.content_type or "application/octet-stream"
    safe_disposition = "inline" if disposition == "inline" else "attachment"
    return StreamingResponse(
        BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f'{safe_disposition}; filename="{filename}"'},
    )


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
    result = [
        _serialize_document(doc)
        for doc in sorted(
            projet.documents,
            key=lambda d: d.created_at,
            reverse=True,
        )
    ]
    # Remplacer les URLs Minio internes par l'URL proxy (web et mobile)
    base = (getattr(settings, "API_PUBLIC_BASE_URL", None) or "").strip().rstrip("/")
    if base:
        result = [
            r.model_copy(update={"download_url": _build_document_proxy_url(r.id)})
            if r.download_url and _is_internal_minio_url(r.download_url)
            else r
            for r in result
        ]
    return result


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

    bucket_name = MinioService.BUCKET_PROJECT_DOCUMENTS
    stored_key = object_name
    try:
        minio_service = MinioService()
        MinioService.ensure_project_documents_bucket()
        minio_service.upload_file(
            MinioService.BUCKET_PROJECT_DOCUMENTS,
            object_name,
            file_bytes,
            content_type=content_type,
        )
    except Exception as storage_error:
        logger.warning(
            "Upload MinIO document projet échoué (projet %s): %s",
            projet.id,
            storage_error,
        )
        ext = "bin"
        if "." in sanitized_name:
            ext = sanitized_name.rsplit(".", 1)[-1].lower()[:12] or "bin"
        if ext not in ("pdf", "jpg", "jpeg", "png", "gif", "webp"):
            ct = (content_type or "").lower()
            if "pdf" in ct:
                ext = "pdf"
            elif "png" in ct:
                ext = "png"
            elif "jpeg" in ct or "jpg" in ct:
                ext = "jpg"
            else:
                ext = "bin"
        rel = write_local_project_file(projet.id, ext, file_bytes)
        if not rel:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stockage de fichiers indisponible (MinIO et répertoire local non configuré).",
            ) from storage_error
        bucket_name = LOCAL_PROJECT_DOCUMENTS_BUCKET
        stored_key = rel

    document = ProjetVoyageDocument(
        projet_voyage_id=projet.id,
        doc_type=doc_type,
        display_name=display_name.strip() if display_name else original_name,
        bucket_name=bucket_name,
        object_name=stored_key,
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
