import logging
from io import BytesIO
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload, selectinload
import httpx
from app.core.database import get_db
from app.api.v1.auth import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.souscription import Souscription
from app.models.attestation import Attestation
from app.models.validation_attestation import ValidationAttestation
from app.models.paiement import Paiement
from app.models.questionnaire import Questionnaire
from app.models.projet_voyage import ProjetVoyage
from app.models.projet_voyage_document import ProjetVoyageDocument
from app.schemas.attestation import (
    AttestationResponse,
    AttestationWithURLResponse,
    AttestationVerificationResponse,
    AttestationReviewItem,
    DocumentReviewInline,
    QuestionnaireInline,
    ValidationState,
)
from app.schemas.validation_attestation import ValidationAttestationCreate, ValidationAttestationResponse
from app.services.attestation_service import (
    AttestationService,
    INLINE_BUCKET_NAME,
    INLINE_OBJECT_KEY,
)
from app.services.notification_service import NotificationService
from app.services.minio_service import MinioService
from app.core.enums import Role, StatutSouscription, StatutPaiement
from app.core.config import settings
from app.core.security import create_ecard_access_token, decode_ecard_token, decode_download_access_token, create_download_access_token

router = APIRouter()
logger = logging.getLogger(__name__)


def _is_internal_minio_url(url: Optional[str]) -> bool:
    if not url:
        return False
    u = (url or "").lower()
    return "minio:" in u or "localhost:9000" in u or "127.0.0.1:9000" in u


def _get_ecard_public_base(request: Optional[Request] = None) -> str:
    """Base URL (sans /api/v1) pour les liens e-carte. Env d'abord, sinon déduit de la requête."""
    base = (getattr(settings, "API_PUBLIC_BASE_URL", None) or "").strip().rstrip("/")
    if base:
        return base
    if request:
        host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").strip()
        proto = (request.headers.get("x-forwarded-proto") or "https").strip().lower()
        if host:
            return f"{proto}://{host}".rstrip("/")
    return ""


def _use_ecard_proxy_url(request: Optional[Request] = None) -> bool:
    """True si MinIO est interne et on a une base publique (env ou requête)."""
    endpoint = (getattr(settings, "MINIO_ENDPOINT", None) or "").lower()
    if "minio" not in endpoint and "localhost" not in endpoint and "127.0.0.1" not in endpoint:
        return False
    return bool(_get_ecard_public_base(request))


def _build_ecard_proxy_url(attestation_id: int, request: Optional[Request] = None) -> str:
    """Construit l'URL de proxy API pour l'e-carte."""
    base = _get_ecard_public_base(request).rstrip("/")
    if not base:
        return ""
    token = create_ecard_access_token(attestation_id)
    return f"{base}/api/v1/attestations/{attestation_id}/ecard/download?token={token}"


def _build_pdf_proxy_url(attestation_id: int, request: Optional[Request] = None) -> str:
    """Construit l'URL de proxy API pour le PDF (contourne minio:9000 pour web et mobile)."""
    base = _get_ecard_public_base(request).rstrip("/")
    if not base:
        return ""
    return f"{base}/api/v1/attestations/{attestation_id}/download"


def _build_projet_document_proxy_url(document_id: int, request: Optional[Request] = None) -> str:
    """URL de proxy pour télécharger une pièce jointe projet (contourne minio:9000)."""
    base = _get_ecard_public_base(request).rstrip("/")
    if not base:
        return ""
    return f"{base}/api/v1/voyages/documents/{document_id}/download"


def _serialize_document_for_review(doc: ProjetVoyageDocument) -> DocumentReviewInline:
    """Pièce jointe du projet de voyage avec URL de téléchargement signée pour consultation dans le modal."""
    download_url: Optional[str] = None
    try:
        download_url = MinioService.generate_signed_url(
            doc.bucket_name,
            doc.object_name,
            expires=timedelta(minutes=30),
        )
    except Exception:
        pass
    return DocumentReviewInline(
        id=doc.id,
        doc_type=doc.doc_type or "",
        display_name=doc.display_name or "",
        content_type=doc.content_type,
        file_size=doc.file_size or 0,
        uploaded_at=doc.uploaded_at,
        download_url=download_url,
    )

_VALIDATION_TYPE_ALIASES = {"agpmh": "production"}
_QUESTIONNAIRE_TYPES = ("short", "long", "administratif", "medical")
_SUBSCRIPTION_VALIDATION_FIELDS = {
    "medecin": (
        "validation_medicale",
        "validation_medicale_notes",
        "validation_medicale_par",
        "validation_medicale_date",
    ),
    "technique": (
        "validation_technique",
        "validation_technique_notes",
        "validation_technique_par",
        "validation_technique_date",
    ),
    "production": (
        "validation_finale",
        "validation_finale_notes",
        "validation_finale_par",
        "validation_finale_date",
    ),
}

_VALIDATION_ROLE_MATRIX = {
    "medecin": {Role.MEDICAL_REVIEWER, Role.DOCTOR, Role.MEDECIN_REFERENT_MH},
    "technique": {Role.TECHNICAL_REVIEWER, Role.FINANCE_MANAGER, Role.HOSPITAL_ADMIN, Role.ADMIN},
    "production": {Role.PRODUCTION_AGENT, Role.ADMIN},
}

_VALIDATION_ROLE_ERRORS = {
    "medecin": "Seuls les médecins ou référents MH peuvent valider médicalement",
    "technique": "Accès réservé aux agents techniques MH",
    "production": "Seuls les agents de production MH peuvent valider définitivement",
}


def _normalize_validation_type(value: str) -> str:
    return _VALIDATION_TYPE_ALIASES.get(value, value)


def _normalize_status_value(value: Optional[str]) -> str:
    return value or "pending"


def _build_validation_states(souscription: Souscription) -> Dict[str, ValidationState]:
    states: Dict[str, ValidationState] = {}
    for key, fields in _SUBSCRIPTION_VALIDATION_FIELDS.items():
        status_field, notes_field, reviewer_field, date_field = fields
        states[key] = ValidationState(
            status=_normalize_status_value(getattr(souscription, status_field, None)),
            notes=getattr(souscription, notes_field, None),
            reviewer_id=getattr(souscription, reviewer_field, None),
            decided_at=getattr(souscription, date_field, None),
        )
    return states


def _collect_latest_questionnaires(
    db: Session,
    subscription_ids: List[int],
) -> Dict[Tuple[int, str], Questionnaire]:
    if not subscription_ids:
        return {}

    questionnaires = (
        db.query(Questionnaire)
        .filter(
            Questionnaire.souscription_id.in_(subscription_ids),
            Questionnaire.statut != "archive",
        )
        .order_by(
            Questionnaire.souscription_id,
            Questionnaire.type_questionnaire,
            Questionnaire.version.desc(),
            Questionnaire.created_at.desc(),
        )
        .all()
    )

    latest: Dict[Tuple[int, str], Questionnaire] = {}
    for questionnaire in questionnaires:
        key = (questionnaire.souscription_id, questionnaire.type_questionnaire)
        if key in latest:
            continue
        latest[key] = questionnaire
    return latest


def _serialize_questionnaires(
    subscription_id: int,
    questionnaires_map: Dict[Tuple[int, str], Questionnaire],
) -> Dict[str, QuestionnaireInline | None]:
    payload: Dict[str, QuestionnaireInline | None] = {}
    for questionnaire_type in _QUESTIONNAIRE_TYPES:
        questionnaire = questionnaires_map.get((subscription_id, questionnaire_type))
        if not questionnaire:
            continue
        payload[questionnaire_type] = QuestionnaireInline(
            id=questionnaire.id,
            type_questionnaire=questionnaire.type_questionnaire,
            version=questionnaire.version,
            statut=questionnaire.statut,
            reponses=questionnaire.reponses or {},
            notes=questionnaire.notes,
            created_at=questionnaire.created_at,
            updated_at=questionnaire.updated_at,
        )
    return payload


def _to_float_or_none(value: Optional[object]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_required_pre_reviews(db: Session, attestation_id: int) -> bool:
    validations = db.query(ValidationAttestation).filter(
        ValidationAttestation.attestation_id == attestation_id,
        ValidationAttestation.type_validation.in_(["medecin"]),
    ).all()

    completed = {
        _normalize_validation_type(validation.type_validation)
        for validation in validations
    }
    return {"medecin"}.issubset(completed)


def _notify_production_agents_if_ready(
    db: Session,
    souscription: Optional[Souscription],
    attestation: Optional[Attestation],
    medical_favorable: Optional[bool] = None,
) -> None:
    if not souscription or not attestation:
        return

    if not _has_required_pre_reviews(db, attestation.id):
        return

    existing_production_validation = db.query(ValidationAttestation).filter(
        ValidationAttestation.attestation_id == attestation.id,
        ValidationAttestation.type_validation.in_(["production", "agpmh"]),
    ).first()

    if existing_production_validation:
        return

    reviewers = db.query(User).filter(
        User.role.in_({Role.PRODUCTION_AGENT, Role.ADMIN}),
        User.is_active == True,  # noqa: E712 - SQLAlchemy convention
    ).all()

    if not reviewers:
        return

    if medical_favorable is False:
        titre = "Avis médical défavorable — décision production requise"
        message = (
            f"La souscription #{souscription.numero_souscription} a reçu un avis médical défavorable. "
            "Merci de statuer en validation définitive (confirmation du refus ou suite à donner)."
        )
    else:
        titre = "Validation technique et définitive requise"
        message = (
            f"La souscription #{souscription.numero_souscription} "
            "dispose de l'avis médical. Merci de valider la décision technique et définitive."
        )

    for reviewer in reviewers:
        NotificationService.create_notification(
            user_id=reviewer.id,
            type_notification="production_review_required",
            titre=titre,
            message=message,
            lien_relation_id=attestation.id,
            lien_relation_type="attestation",
            channels=["push"],
        )


def _update_subscription_validation_state(
    souscription: Optional[Souscription],
    validation_type: str,
    is_valid: bool,
    notes: Optional[str],
    user_id: int,
    decision_date: datetime,
) -> None:
    if not souscription:
        return

    status_value = "approved" if is_valid else "rejected"

    if validation_type == "medecin":
        souscription.validation_medicale = status_value
        souscription.validation_medicale_par = user_id
        souscription.validation_medicale_date = decision_date
        souscription.validation_medicale_notes = notes
    elif validation_type == "technique":
        souscription.validation_technique = status_value
        souscription.validation_technique_par = user_id
        souscription.validation_technique_date = decision_date
        souscription.validation_technique_notes = notes
    elif validation_type == "production":
        souscription.validation_finale = status_value
        souscription.validation_finale_par = user_id
        souscription.validation_finale_date = decision_date
        souscription.validation_finale_notes = notes
        souscription.statut = (
            StatutSouscription.ACTIVE if is_valid else StatutSouscription.RESILIEE
        )


@router.get("/subscriptions/{subscription_id}/attestations", response_model=List[AttestationResponse])
async def get_subscription_attestations(
    request: Request,
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir toutes les attestations d'une souscription"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 Recherche d'attestations pour souscription {subscription_id} (utilisateur {current_user.id})")
    
    # Vérifier que la souscription existe et appartient à l'utilisateur
    souscription = db.query(Souscription).filter(
        Souscription.id == subscription_id,
        Souscription.user_id == current_user.id
    ).first()
    
    if not souscription:
        logger.warning(f"❌ Souscription {subscription_id} non trouvée ou n'appartient pas à l'utilisateur {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    logger.info(f"✅ Souscription trouvée: {souscription.numero_souscription} (statut: {souscription.statut})")
    
    # Rechercher toutes les attestations pour cette souscription
    attestations = db.query(Attestation).filter(
        Attestation.souscription_id == subscription_id
    ).order_by(Attestation.created_at.desc()).all()
    
    logger.info(f"📋 Nombre d'attestations trouvées: {len(attestations)}")
    
    # Log détaillé des attestations trouvées
    if len(attestations) > 0:
        for att in attestations:
            logger.info(
                f"   - Attestation ID {att.id}: type={att.type_attestation}, "
                f"numero={att.numero_attestation}, valide={att.est_valide}, "
                f"chemin={att.chemin_fichier_minio}"
            )
    else:
        # Vérifier s'il y a des attestations invalides ou supprimées
        total_attestations = db.query(Attestation).filter(
            Attestation.souscription_id == subscription_id
        ).count()
        if total_attestations > 0:
            logger.warning(f"⚠️ {total_attestations} attestation(s) trouvée(s) mais peut-être invalide(s)")
            attestations_invalides = db.query(Attestation).filter(
                Attestation.souscription_id == subscription_id,
                Attestation.est_valide == False
            ).all()
            if attestations_invalides:
                logger.warning(f"   {len(attestations_invalides)} attestation(s) invalide(s) trouvée(s)")
    
    # Si aucune attestation et que la souscription est en attente, vérifier s'il y a un paiement
    # et créer une attestation provisoire si nécessaire
    if len(attestations) == 0 and souscription.statut in [StatutSouscription.EN_ATTENTE, "en_attente", "pending"]:
        logger.info(f"🔍 Souscription {subscription_id} en attente sans attestation, recherche d'un paiement...")
        
        # Chercher tous les paiements pour cette souscription (pour diagnostic)
        tous_paiements = db.query(Paiement).filter(
            Paiement.souscription_id == subscription_id
        ).all()
        
        logger.info(f"📊 Paiements trouvés pour souscription {subscription_id}: {len(tous_paiements)}")
        for p in tous_paiements:
            logger.info(f"   - Paiement ID {p.id}: statut={p.statut}, montant={p.montant}, date={p.created_at}")
        
        # Chercher un paiement valide pour cette souscription
        paiement = db.query(Paiement).filter(
            Paiement.souscription_id == subscription_id,
            Paiement.statut == StatutPaiement.VALIDE.name
        ).order_by(Paiement.created_at.desc()).first()
        
        if paiement:
            logger.info(f"💡 Paiement VALIDE trouvé (ID: {paiement.id}) pour souscription {subscription_id}, création d'une attestation provisoire")
            try:
                from app.services.attestation_service import AttestationService
                attestation_provisoire = AttestationService.create_attestation_provisoire(
                    db=db,
                    souscription=souscription,
                    paiement=paiement,
                    user=current_user
                )
                attestations = [attestation_provisoire]
                logger.info(f"✅ Attestation provisoire créée: {attestation_provisoire.numero_attestation} (ID: {attestation_provisoire.id})")
            except Exception as e:
                logger.error(f"❌ Erreur lors de la création de l'attestation provisoire: {e}", exc_info=True)
        else:
            logger.warning(f"⚠️ Aucune attestation et aucun paiement VALIDE pour souscription {subscription_id} en attente")
            if len(tous_paiements) > 0:
                statuts_paiements = [p.statut for p in tous_paiements]
                logger.warning(f"   Paiements existants mais avec statuts: {statuts_paiements}")
            logger.warning(f"💡 L'attestation provisoire sera créée lors du paiement (checkout)")
    
    if len(attestations) == 0:
        # Vérifier s'il y a des attestations pour cette souscription sans filtre utilisateur
        total_attestations = db.query(Attestation).filter(
            Attestation.souscription_id == subscription_id
        ).count()
        logger.warning(f"⚠️ Aucune attestation retournée pour souscription {subscription_id} (total en base: {total_attestations})")
    else:
        logger.info(f"📄 Types d'attestations trouvées: {[att.type_attestation for att in attestations]}")
    
    # Générer les URLs à la volée à partir de la clé stockée (NE JAMAIS utiliser les URLs stockées en base)
    from app.services.minio_service import MinioService
    now = datetime.utcnow()
    expires = timedelta(hours=24)  # 24h d'expiration (au lieu de 2h)
    
    for attestation in attestations:
        # Générer une URL fraîche pour le PDF si ce n'est pas un stockage inline
        uses_inline_storage = attestation.bucket_minio == INLINE_BUCKET_NAME or \
            attestation.chemin_fichier_minio == INLINE_OBJECT_KEY
        
        if not uses_inline_storage and attestation.chemin_fichier_minio:
            try:
                # Générer une nouvelle URL signée à partir de la clé (NE PAS stocker en base)
                fresh_url = MinioService.get_pdf_url(
                    attestation.chemin_fichier_minio,
                    attestation.bucket_minio,
                    expires
                )
                # Mettre à jour uniquement pour la réponse (pas de commit en base)
                attestation.url_signee = fresh_url
                attestation.date_expiration_url = now + expires
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                # Vérifier si c'est une erreur d'URL expirée
                if MinioService.is_expired_url_error(e):
                    logger.warning(
                        f"URL expirée pour l'attestation {attestation.id}. "
                        f"Tentative de régénération..."
                    )
                    try:
                        # Réessayer avec régénération automatique
                        fresh_url = MinioService.get_pdf_url(
                            attestation.chemin_fichier_minio,
                            attestation.bucket_minio,
                            expires
                        )
                        # Mettre à jour uniquement pour la réponse (pas de commit en base)
                        attestation.url_signee = fresh_url
                        attestation.date_expiration_url = now + expires
                        logger.info(f"URL régénérée avec succès pour l'attestation {attestation.id}")
                    except Exception as retry_error:
                        logger.error(
                            f"Échec de la régénération de l'URL pour l'attestation {attestation.id}: {retry_error}. "
                            f"Vérifiez la synchronisation de l'heure du serveur."
                        )
                else:
                    logger.error(f"Erreur lors de la génération de l'URL pour l'attestation {attestation.id}: {e}")
        # Contourner Minio interne (minio:9000) : renvoyer l'URL proxy API pour web et mobile
        if attestation.url_signee and _is_internal_minio_url(attestation.url_signee):
            proxy = _build_pdf_proxy_url(attestation.id, request)
            if proxy:
                attestation.url_signee = proxy
                attestation.date_expiration_url = now + timedelta(hours=24)
        
        # Pour les attestations définitives, générer aussi l'URL de la carte numérique
        if attestation.type_attestation == "definitive" and attestation.carte_numerique_path and attestation.carte_numerique_bucket:
            is_inline_card = attestation.carte_numerique_bucket == INLINE_BUCKET_NAME or \
                attestation.carte_numerique_path == INLINE_OBJECT_KEY
            if not is_inline_card:
                try:
                    if _use_ecard_proxy_url(request):
                        attestation.carte_numerique_url = _build_ecard_proxy_url(attestation.id, request)
                        attestation.carte_numerique_expires_at = now + timedelta(minutes=30)
                    else:
                        fresh_card_url = MinioService.generate_signed_url(
                            attestation.carte_numerique_bucket,
                            attestation.carte_numerique_path,
                            expires
                        )
                        attestation.carte_numerique_url = fresh_card_url
                        attestation.carte_numerique_expires_at = now + expires
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erreur lors de la génération de l'URL de la carte pour l'attestation {attestation.id}: {e}")
        if attestation.carte_numerique_url and _is_internal_minio_url(attestation.carte_numerique_url):
            proxy = _build_ecard_proxy_url(attestation.id, request)
            if proxy:
                attestation.carte_numerique_url = proxy
                attestation.carte_numerique_expires_at = now + timedelta(minutes=30)
    
    logger.info(f"✅ Retour de {len(attestations)} attestation(s) pour souscription {subscription_id}")
    if len(attestations) > 0:
        logger.info(f"📄 Détails des attestations: {[(att.id, att.type_attestation, att.numero_attestation) for att in attestations]}")
    return attestations


@router.get("/users/me/attestations", response_model=List[AttestationResponse])
async def get_user_attestations(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir toutes les attestations de l'utilisateur connecté"""
    attestations = (
        db.query(Attestation)
        .join(Souscription, Attestation.souscription_id == Souscription.id)
        .filter(Souscription.user_id == current_user.id)
        .order_by(Attestation.created_at.desc())
        .all()
    )
    
    # Générer les URLs à la volée à partir de la clé stockée (NE JAMAIS utiliser les URLs stockées en base)
    from app.services.minio_service import MinioService
    now = datetime.utcnow()
    expires = timedelta(hours=24)  # 24h d'expiration (au lieu de 2h)
    
    for attestation in attestations:
        # Générer une URL fraîche pour le PDF si ce n'est pas un stockage inline
        uses_inline_storage = attestation.bucket_minio == INLINE_BUCKET_NAME or \
            attestation.chemin_fichier_minio == INLINE_OBJECT_KEY
        
        if not uses_inline_storage and attestation.chemin_fichier_minio:
            try:
                # Générer une nouvelle URL signée à partir de la clé (NE PAS stocker en base)
                fresh_url = MinioService.get_pdf_url(
                    attestation.chemin_fichier_minio,
                    attestation.bucket_minio,
                    expires
                )
                # Mettre à jour uniquement pour la réponse (pas de commit en base)
                attestation.url_signee = fresh_url
                attestation.date_expiration_url = now + expires
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                # Vérifier si c'est une erreur d'URL expirée
                if MinioService.is_expired_url_error(e):
                    logger.warning(
                        f"URL expirée pour l'attestation {attestation.id}. "
                        f"Tentative de régénération..."
                    )
                    try:
                        # Réessayer avec régénération automatique
                        fresh_url = MinioService.get_pdf_url(
                            attestation.chemin_fichier_minio,
                            attestation.bucket_minio,
                            expires
                        )
                        # Mettre à jour uniquement pour la réponse (pas de commit en base)
                        attestation.url_signee = fresh_url
                        attestation.date_expiration_url = now + expires
                        logger.info(f"URL régénérée avec succès pour l'attestation {attestation.id}")
                    except Exception as retry_error:
                        logger.error(
                            f"Échec de la régénération de l'URL pour l'attestation {attestation.id}: {retry_error}. "
                            f"Vérifiez la synchronisation de l'heure du serveur."
                        )
                else:
                    logger.error(f"Erreur lors de la génération de l'URL pour l'attestation {attestation.id}: {e}")
        # Contourner Minio interne (minio:9000) : renvoyer l'URL proxy API pour web et mobile
        if attestation.url_signee and _is_internal_minio_url(attestation.url_signee):
            proxy = _build_pdf_proxy_url(attestation.id, request)
            if proxy:
                attestation.url_signee = proxy
                attestation.date_expiration_url = now + timedelta(hours=24)
        
        # Pour les attestations définitives, générer aussi l'URL de la carte numérique
        if attestation.type_attestation == "definitive" and attestation.carte_numerique_path and attestation.carte_numerique_bucket:
            is_inline_card = attestation.carte_numerique_bucket == INLINE_BUCKET_NAME or \
                attestation.carte_numerique_path == INLINE_OBJECT_KEY
            if not is_inline_card:
                try:
                    if _use_ecard_proxy_url(request):
                        attestation.carte_numerique_url = _build_ecard_proxy_url(attestation.id, request)
                        attestation.carte_numerique_expires_at = now + timedelta(minutes=30)
                    else:
                        fresh_card_url = MinioService.generate_signed_url(
                            attestation.carte_numerique_bucket,
                            attestation.carte_numerique_path,
                            expires
                        )
                        attestation.carte_numerique_url = fresh_card_url
                        attestation.carte_numerique_expires_at = now + expires
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erreur lors de la génération de l'URL de la carte pour l'attestation {attestation.id}: {e}")
        if attestation.carte_numerique_url and _is_internal_minio_url(attestation.carte_numerique_url):
            proxy = _build_ecard_proxy_url(attestation.id, request)
            if proxy:
                attestation.carte_numerique_url = proxy
                attestation.carte_numerique_expires_at = now + timedelta(minutes=30)
    
    return attestations


@router.get("/attestations/{attestation_id}/ecard/download")
async def download_attestation_ecard(
    attestation_id: int,
    token: Optional[str] = Query(None, description="JWT court pour affichage e-carte (img src)"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Télécharger ou afficher la carte numérique (image). Accepte Bearer ou ?token= pour img src."""
    attestation = db.query(Attestation).filter(
        Attestation.id == attestation_id
    ).first()
    
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation non trouvée"
        )
    
    # Contrôle d'accès : soit token e-carte valide, soit utilisateur connecté avec droits
    if token:
        aid = decode_ecard_token(token)
        if aid is not None and aid == attestation_id:
            pass  # accès autorisé par token
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token e-carte invalide ou expiré"
            )
    else:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentification requise (Bearer ou token e-carte)"
            )
        souscription = db.query(Souscription).filter(
            Souscription.id == attestation.souscription_id
        ).first()
        if not souscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Souscription associée introuvable"
            )
        is_owner = souscription.user_id == current_user.id
        is_reviewer = current_user.role in (Role.PRODUCTION_AGENT, Role.ADMIN)
        if not is_owner and not is_reviewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cette attestation"
            )

    if not attestation.carte_numerique_path or not attestation.carte_numerique_bucket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carte numérique non disponible (fichier non trouvé dans Minio)",
        )

    # Récupérer le fichier directement depuis Minio et le servir
    from app.services.minio_service import MinioService
    from fastapi.responses import StreamingResponse
    from io import BytesIO

    bucket_name = attestation.carte_numerique_bucket or MinioService.BUCKET_ATTESTATIONS

    try:
        # Vérifier que le fichier existe avant de le récupérer
        from app.core.minio_client import minio_client
        from minio.error import S3Error
        
        # Vérifier l'existence du fichier
        try:
            minio_client.stat_object(bucket_name, attestation.carte_numerique_path)
        except S3Error as stat_error:
            error_code = getattr(stat_error, 'code', 'Unknown')
            if error_code == 'NoSuchKey':
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Carte numérique non trouvée dans MinIO: {bucket_name}/{attestation.carte_numerique_path} "
                    f"(Attestation ID: {attestation.id}, Numéro: {attestation.numero_attestation})"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"La carte numérique n'existe pas dans le stockage. "
                           f"Chemin: {attestation.carte_numerique_path}"
                )
            else:
                raise
        
        # Récupérer le fichier depuis Minio
        response = minio_client.get_object(
            bucket_name,
            attestation.carte_numerique_path
        )
        
        # Lire le contenu du fichier
        file_data = response.read()
        response.close()
        response.release_conn()
        
        # Servir le fichier directement
        file_stream = BytesIO(file_data)
        return StreamingResponse(
            file_stream,
            media_type="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="carte-{attestation.numero_attestation}.png"'
            }
        )
    except HTTPException:
        # Re-lancer les HTTPException telles quelles
        raise
    except S3Error as s3_error:
        # Erreur spécifique MinIO/S3
        import logging
        logger = logging.getLogger(__name__)
        
        # Extraire tous les détails de l'erreur
        error_details = MinioService.extract_error_details(s3_error)
        error_code = error_details.get('code') or 'Unknown'
        error_message = error_details.get('message') or str(s3_error)
        resource = error_details.get('resource')
        request_id = error_details.get('request_id')
        
        # Construire un message d'erreur détaillé
        error_info = f"Code: {error_code}, Message: {error_message}"
        if resource:
            error_info += f", Resource: {resource}"
        if request_id:
            error_info += f", RequestId: {request_id}"
        
        logger.error(
            f"Erreur MinIO lors de la récupération de la carte numérique "
            f"{bucket_name}/{attestation.carte_numerique_path}. {error_info}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Impossible d'accéder à la carte numérique. Erreur MinIO: {error_info}"
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"Erreur lors de la récupération de la carte numérique depuis Minio: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du téléchargement de la carte numérique: {str(e)}"
        )


@router.get("/attestations/{attestation_id}/download")
async def download_attestation_pdf(
    attestation_id: int,
    token: Optional[str] = Query(None, description="JWT court pour accès direct au PDF"),
    disposition: str = Query("attachment", description="attachment ou inline"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Télécharger directement le PDF d'une attestation depuis Minio"""
    attestation = db.query(Attestation).filter(
        Attestation.id == attestation_id
    ).first()
    
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation non trouvée"
        )
    
    # Vérifier que l'utilisateur a accès à cette attestation
    souscription = db.query(Souscription).filter(
        Souscription.id == attestation.souscription_id
    ).first()

    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription associée introuvable"
        )
    
    if token:
        aid = decode_download_access_token(token, "attestation_pdf")
        if aid is None or aid != attestation_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token attestation invalide ou expiré"
            )
    else:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentification requise"
            )
        is_owner = souscription.user_id == current_user.id
        is_reviewer = current_user.role in (Role.PRODUCTION_AGENT, Role.ADMIN)
        if not is_owner and not is_reviewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cette attestation"
            )

    # Vérifier si c'est un stockage inline
    from app.services.attestation_service import INLINE_BUCKET_NAME, INLINE_OBJECT_KEY
    uses_inline_storage = attestation.bucket_minio == INLINE_BUCKET_NAME or \
        attestation.chemin_fichier_minio == INLINE_OBJECT_KEY
    
    if uses_inline_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation stockée en mode inline, téléchargement non disponible"
        )

    if not attestation.chemin_fichier_minio or not attestation.bucket_minio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF non disponible (fichier non trouvé dans Minio)",
        )

    # Récupérer le fichier directement depuis Minio et le servir
    from app.services.minio_service import MinioService

    bucket_name = attestation.bucket_minio or MinioService.BUCKET_ATTESTATIONS

    safe_disposition = "inline" if disposition == "inline" else "attachment"
    try:
        # Vérifier que le fichier existe avant de le récupérer
        from app.core.minio_client import minio_client
        from minio.error import S3Error
        
        # Vérifier l'existence du fichier
        try:
            minio_client.stat_object(bucket_name, attestation.chemin_fichier_minio)
        except S3Error as stat_error:
            error_code = getattr(stat_error, 'code', 'Unknown')
            if error_code == 'NoSuchKey':
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"PDF non trouvé dans MinIO: {bucket_name}/{attestation.chemin_fichier_minio} "
                    f"(Attestation ID: {attestation.id}, Numéro: {attestation.numero_attestation})"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Le PDF n'existe pas dans le stockage. "
                           f"Chemin: {attestation.chemin_fichier_minio}"
                )
            else:
                raise
        
        # Récupérer le fichier depuis Minio
        response = minio_client.get_object(
            bucket_name,
            attestation.chemin_fichier_minio
        )
        
        # Lire le contenu du fichier
        file_data = response.read()
        response.close()
        response.release_conn()
        
        # Servir le fichier directement
        file_stream = BytesIO(file_data)
        return StreamingResponse(
            file_stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'{safe_disposition}; filename="attestation-{attestation.numero_attestation}.pdf"'
            }
        )
    except HTTPException:
        # Re-lancer les HTTPException telles quelles
        raise
    except S3Error as s3_error:
        # Fallback : récupérer via URL signée côté serveur et streamer (évite échec client sur Minio)
        error_details = MinioService.extract_error_details(s3_error)
        error_message = error_details.get('message') or str(s3_error)
        logger.warning(
            f"Erreur MinIO lors de la récupération directe du PDF, tentative fallback URL signée: {error_message}"
        )
        try:
            url_signee = AttestationService.refresh_signed_url(
                db=db, attestation=attestation, expires=timedelta(hours=1)
            )
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url_signee)
                resp.raise_for_status()
                content = resp.content
            return StreamingResponse(
                BytesIO(content),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'{safe_disposition}; filename="attestation-{attestation.numero_attestation}.pdf"'
                },
            )
        except Exception as fallback_err:
            logger.error(f"Fallback URL signée échoué: {fallback_err}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Impossible de récupérer le PDF. MinIO: {error_message}"
            )
    except Exception as e:
        logger.warning(f"Erreur inattendue lors de la récupération du PDF, tentative fallback: {e}", exc_info=True)
        try:
            url_signee = AttestationService.refresh_signed_url(
                db=db, attestation=attestation, expires=timedelta(hours=1)
            )
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url_signee)
                resp.raise_for_status()
                content = resp.content
            return StreamingResponse(
                BytesIO(content),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'{safe_disposition}; filename="attestation-{attestation.numero_attestation}.pdf"'
                },
            )
        except Exception as fallback_err:
            logger.error(f"Fallback URL signée échoué: {fallback_err}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Erreur lors de la récupération du PDF. Réessayez plus tard."
            )


@router.get("/attestations/{attestation_id}", response_model=AttestationWithURLResponse)
async def get_attestation_with_url(
    request: Request,
    attestation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir une attestation avec URL signée (rafraîchit l'URL si nécessaire)"""
    attestation = db.query(Attestation).filter(
        Attestation.id == attestation_id
    ).first()
    
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation non trouvée"
        )
    
    # Vérifier que l'utilisateur a accès à cette attestation
    souscription = db.query(Souscription).filter(
        Souscription.id == attestation.souscription_id
    ).first()

    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription associée introuvable"
        )
    
    # Accès : propriétaire de la souscription, ou agent de production / admin (pour consulter les attestations en revue)
    is_owner = souscription and souscription.user_id == current_user.id
    is_reviewer = current_user.role in (Role.PRODUCTION_AGENT, Role.ADMIN)
    if not souscription or (not is_owner and not is_reviewer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé à cette attestation"
        )
    
    # Générer les URLs à la volée à partir de la clé stockée (NE JAMAIS utiliser les URLs stockées en base)
    from app.services.minio_service import MinioService
    now = datetime.utcnow()
    expires = timedelta(hours=24)  # 24h d'expiration (au lieu de 2h)
    
    # Vérifier l'heure du serveur pour diagnostiquer les problèmes
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"🕐 Heure serveur UTC: {now.isoformat()}")
    
    uses_inline_storage = attestation.bucket_minio == INLINE_BUCKET_NAME or \
        attestation.chemin_fichier_minio == INLINE_OBJECT_KEY

    # Générer une URL fraîche pour le PDF si ce n'est pas un stockage inline
    if not uses_inline_storage and attestation.chemin_fichier_minio:
        try:
            url_signee = MinioService.get_pdf_url(
                attestation.chemin_fichier_minio,
                attestation.bucket_minio,
                expires
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            # Vérifier si c'est une erreur d'URL expirée
            if MinioService.is_expired_url_error(e):
                logger.warning(
                    f"URL expirée pour l'attestation {attestation.id}. "
                    f"Tentative de régénération..."
                )
                try:
                    # Réessayer avec régénération automatique
                    url_signee = MinioService.get_pdf_url(
                        attestation.chemin_fichier_minio,
                        attestation.bucket_minio,
                        expires
                    )
                    logger.info(f"URL régénérée avec succès pour l'attestation {attestation.id}")
                except Exception as retry_error:
                    logger.error(
                        f"Échec de la régénération de l'URL pour l'attestation {attestation.id}: {retry_error}. "
                        f"Vérifiez la synchronisation de l'heure du serveur."
                    )
                    url_signee = attestation.url_signee or None
            else:
                logger.error(f"Erreur lors de la génération de l'URL pour l'attestation {attestation.id}: {e}")
                url_signee = attestation.url_signee or None
    else:
        url_signee = attestation.url_signee
    
    # Contourner Minio interne (minio:9000) : renvoyer l'URL proxy API pour web et mobile
    if url_signee and _is_internal_minio_url(url_signee):
        proxy = _build_pdf_proxy_url(attestation.id, request)
        if proxy:
            url_signee = proxy
    
    # Pour les attestations définitives, générer aussi l'URL de la carte numérique
    carte_numerique_url = None
    carte_numerique_expires_at = None
    if attestation.type_attestation == "definitive" and attestation.carte_numerique_path and attestation.carte_numerique_bucket:
        is_inline_card = attestation.carte_numerique_bucket == INLINE_BUCKET_NAME or \
            attestation.carte_numerique_path == INLINE_OBJECT_KEY
        if not is_inline_card:
            try:
                if _use_ecard_proxy_url(request):
                    carte_numerique_url = _build_ecard_proxy_url(attestation.id, request)
                    carte_numerique_expires_at = now + timedelta(minutes=30)
                else:
                    carte_numerique_url = MinioService.generate_signed_url(
                        attestation.carte_numerique_bucket,
                        attestation.carte_numerique_path,
                        expires
                    )
                    carte_numerique_expires_at = now + expires
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erreur lors de la génération de l'URL de la carte pour l'attestation {attestation.id}: {e}")
                carte_numerique_url = attestation.carte_numerique_url
                carte_numerique_expires_at = attestation.carte_numerique_expires_at
    else:
        carte_numerique_url = attestation.carte_numerique_url
        carte_numerique_expires_at = attestation.carte_numerique_expires_at
    if carte_numerique_url and _is_internal_minio_url(carte_numerique_url):
        proxy = _build_ecard_proxy_url(attestation.id, request)
        if proxy:
            carte_numerique_url = proxy
            carte_numerique_expires_at = now + timedelta(minutes=30)
    
    return AttestationWithURLResponse(
        id=attestation.id,
        type_attestation=attestation.type_attestation,
        numero_attestation=attestation.numero_attestation,
        url_signee=url_signee or "",
        date_expiration_url=now + expires if url_signee else None,
        carte_numerique_url=carte_numerique_url,
        carte_numerique_expires_at=carte_numerique_expires_at,
        created_at=attestation.created_at
    )


@router.get("/attestations/reviews/{validation_type}", response_model=List[AttestationReviewItem])
async def get_attestation_reviews(
    request: Request,
    validation_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lister les attestations provisoires en attente pour un type de validation donné."""
    normalized_type = _normalize_validation_type(validation_type)

    if normalized_type not in _VALIDATION_ROLE_MATRIX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type de validation inconnu"
        )

    allowed_roles = _VALIDATION_ROLE_MATRIX[normalized_type]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_VALIDATION_ROLE_ERRORS.get(normalized_type, "Accès non autorisé pour cette validation")
        )

    attestations = (
        db.query(Attestation)
        .options(
            joinedload(Attestation.souscription).joinedload(Souscription.user),
            joinedload(Attestation.souscription).joinedload(Souscription.produit_assurance),
            joinedload(Attestation.souscription).joinedload(Souscription.projet_voyage),
            joinedload(Attestation.validations),
        )
        .filter(Attestation.type_attestation == "provisoire")
        .order_by(Attestation.created_at.desc())
        .all()
    )

    subscription_ids = [att.souscription_id for att in attestations]
    questionnaires_map = _collect_latest_questionnaires(db, subscription_ids)

    review_items: List[AttestationReviewItem] = []

    for attestation in attestations:
        souscription = attestation.souscription
        if not souscription:
            continue

        validation_states = _build_validation_states(souscription)
        current_state = validation_states.get(normalized_type)

        # Ne garder que les dossiers en attente de validation pour ce type
        # (en production : une fois approuvé ou refusé, le dossier disparaît de la liste)
        if not current_state or current_state.status != "pending":
            continue

        questionnaires_payload = _serialize_questionnaires(souscription.id, questionnaires_map)

        client = souscription.user
        produit = getattr(souscription, "produit_assurance", None)

        # Extraire les informations du tiers si la souscription est pour un tiers
        is_tier_subscription = False
        tier_info = {}
        
        # Vérifier si c'est une souscription pour un tiers
        from app.models.projet_voyage import ProjetVoyage
        projet = None
        if souscription.projet_voyage_id:
            projet = db.query(ProjetVoyage).filter(
                ProjetVoyage.id == souscription.projet_voyage_id
            ).first()
            if projet and projet.notes and ("Pour un tiers" in projet.notes or "pour un tiers" in projet.notes.lower()):
                is_tier_subscription = True
        
        if not is_tier_subscription and souscription.notes:
            if "Pour un tiers" in souscription.notes or "pour un tiers" in souscription.notes.lower():
                is_tier_subscription = True
        
        # Si c'est une souscription pour un tiers, extraire les informations du tiers
        if is_tier_subscription:
            tier_info = AttestationService._extract_traveler_info(db, souscription.id)
            # Si les informations du tiers sont vides, essayer d'extraire depuis les notes
            if not tier_info.get("fullName"):
                if projet and projet.notes:
                    tier_info = AttestationService._extract_tier_info_from_notes(projet.notes)
                if not tier_info.get("fullName") and souscription.notes:
                    tier_info = AttestationService._extract_tier_info_from_notes(souscription.notes)

        attestation_download_url = None
        pdf_proxy_url = _build_pdf_proxy_url(attestation.id, request)
        if pdf_proxy_url:
            attestation_token = create_download_access_token("attestation_pdf", attestation.id)
            separator = "&" if "?" in pdf_proxy_url else "?"
            attestation_download_url = f"{pdf_proxy_url}{separator}token={attestation_token}"

        # Pièces jointes du projet de voyage (consultables depuis le modal)
        documents_projet_voyage: List[DocumentReviewInline] = []
        try:
            pv_id = getattr(souscription, "projet_voyage_id", None)
            if pv_id:
                docs = (
                    db.query(ProjetVoyageDocument)
                    .filter(ProjetVoyageDocument.projet_voyage_id == pv_id)
                    .order_by(ProjetVoyageDocument.uploaded_at.desc())
                    .all()
                )
                documents_projet_voyage = [_serialize_document_for_review(d) for d in docs]
                # Contourner Minio : remplacer les URLs internes par le proxy API
                base = _get_ecard_public_base(request).rstrip("/")
                if base:
                    documents_projet_voyage = [
                        d.model_copy(
                            update={
                                "download_url": (
                                    lambda base_url: f"{base_url}{'&' if '?' in base_url else '?'}token={create_download_access_token('project_document', d.id)}"
                                )(_build_projet_document_proxy_url(d.id, request))
                            }
                        )
                        if d.download_url
                        else d
                        for d in documents_projet_voyage
                    ]
        except Exception:
            documents_projet_voyage = []

        # Enfants mineurs à charge (notes souscription puis projet)
        minors_info = AttestationService._extract_minors_from_notes(souscription.notes or "")
        if not minors_info and projet and getattr(projet, "notes", None):
            minors_info = AttestationService._extract_minors_from_notes(projet.notes)

        review_items.append(
            AttestationReviewItem(
                attestation_id=attestation.id,
                attestation_type=attestation.type_attestation,
                numero_attestation=attestation.numero_attestation,
                attestation_download_url=attestation_download_url,
                attestation_created_at=attestation.created_at,
                souscription_id=souscription.id,
                numero_souscription=souscription.numero_souscription,
                souscription_status=souscription.statut.value
                if hasattr(souscription.statut, "value")
                else souscription.statut,
                prix_applique=_to_float_or_none(souscription.prix_applique),
                currency=(getattr(produit, "currency", None) or "XAF") if produit else "XAF",
                date_debut=souscription.date_debut,
                date_fin=souscription.date_fin,
                client_id=client.id if client else None,
                client_name=(client.full_name or client.username) if client else None,
                client_email=client.email if client else None,
                # Informations personnelles depuis l'inscription
                client_date_naissance=client.date_naissance if client else None,
                client_telephone=client.telephone if client else None,
                client_sexe=client.sexe if client else None,
                client_nationalite=client.nationalite if client else None,
                client_numero_passeport=client.numero_passeport if client else None,
                client_validite_passeport=client.validite_passeport if client else None,
                client_pays_residence=client.pays_residence if client else None,
                client_contact_urgence=client.contact_urgence if client else None,
                client_maladies_chroniques=getattr(client, "maladies_chroniques", None) if client else None,
                client_traitements_en_cours=getattr(client, "traitements_en_cours", None) if client else None,
                client_antecedents_recents=getattr(client, "antecedents_recents", None) if client else None,
                client_grossesse=getattr(client, "grossesse", None) if client else None,
                produit_nom=produit.nom if produit else None,
                # Informations du tiers (si applicable)
                is_tier_subscription=is_tier_subscription,
                tier_full_name=tier_info.get("fullName") if tier_info else None,
                tier_birth_date=tier_info.get("birthDate") if tier_info else None,
                tier_gender=tier_info.get("gender") if tier_info else None,
                tier_nationality=tier_info.get("nationality") if tier_info else None,
                tier_passport_number=tier_info.get("passportNumber") if tier_info else None,
                tier_passport_expiry_date=tier_info.get("passportExpiryDate") if tier_info else None,
                tier_phone=tier_info.get("phone") if tier_info else None,
                tier_email=tier_info.get("email") if tier_info else None,
                tier_address=tier_info.get("address") if tier_info else None,
                validation_type=normalized_type,
                validation_status=current_state.status,
                validations=validation_states,
                questionnaires=questionnaires_payload,
                documents_projet_voyage=documents_projet_voyage or None,
                minors_info=minors_info or None,
            )
        )

    return review_items


@router.post("/attestations/{attestation_id}/validations", response_model=ValidationAttestationResponse)
async def create_validation(
    attestation_id: int,
    validation: ValidationAttestationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer une validation pour une attestation (médecin, production)"""
    # Vérifier que l'attestation existe
    attestation = db.query(Attestation).filter(
        Attestation.id == attestation_id
    ).first()
    
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation non trouvée"
        )
    
    souscription = db.query(Souscription).filter(
        Souscription.id == attestation.souscription_id
    ).first()

    normalized_type = _normalize_validation_type(validation.type_validation)
    
    if normalized_type not in _VALIDATION_ROLE_MATRIX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type de validation inconnu"
        )

    allowed_roles = _VALIDATION_ROLE_MATRIX[normalized_type]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_VALIDATION_ROLE_ERRORS.get(normalized_type, "Accès non autorisé pour cette validation")
        )

    # L'agent de production peut valider les attestations provisoires directement pour générer
    # l'attestation définitive, sans exiger une validation médicale préalable sur l'attestation.
    # if normalized_type == "production" and not _has_required_pre_reviews(db, attestation_id):
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="La validation médicale doit être complétée avant la validation technique et définitive."
    #     )

    type_filters = [normalized_type]
    if normalized_type == "production":
        type_filters.append("agpmh")

    existing_validation = db.query(ValidationAttestation).filter(
        ValidationAttestation.attestation_id == attestation_id,
        ValidationAttestation.type_validation.in_(type_filters)
    ).first()
    
    validation_timestamp = datetime.utcnow()
    
    if existing_validation:
        existing_validation.est_valide = validation.est_valide
        existing_validation.commentaires = validation.commentaires
        existing_validation.valide_par_user_id = current_user.id
        existing_validation.date_validation = validation_timestamp if validation.est_valide else None
        existing_validation.type_validation = normalized_type
        validation_obj = existing_validation
    else:
        validation_obj = ValidationAttestation(
            attestation_id=attestation_id,
            type_validation=normalized_type,
            est_valide=validation.est_valide,
            commentaires=validation.commentaires,
            valide_par_user_id=current_user.id,
            date_validation=validation_timestamp if validation.est_valide else None
        )
        db.add(validation_obj)

    _update_subscription_validation_state(
        souscription,
        normalized_type,
        validation.est_valide,
        validation.commentaires,
        current_user.id,
        validation_timestamp,
    )

    db.flush()

    if normalized_type == "medecin":
        _notify_production_agents_if_ready(db, souscription, attestation, validation.est_valide)

    # Persister la validation tout de suite pour que le client reçoive 200 même si la suite (carte, etc.) échoue ou est lente
    db.commit()
    db.refresh(validation_obj)

    # Si la validation de production est validée : créer l'attestation définitive si elle n'existe pas, puis carte si besoin
    # (bloc isolé en try/except pour ne jamais faire échouer la requête)
    try:
        if normalized_type == "production" and validation.est_valide:
            # Vérifier si une attestation définitive existe
            definitive_created_this_request = False
            existing_definitive = db.query(Attestation).filter(
                Attestation.souscription_id == souscription.id,
                Attestation.type_attestation == "definitive"
            ).first()

            if not existing_definitive:
                # Créer l'attestation définitive (paiement valide + user requis)
                paiement = db.query(Paiement).filter(
                    Paiement.souscription_id == souscription.id,
                    Paiement.statut == StatutPaiement.VALIDE.name
                ).order_by(Paiement.created_at.desc()).first()
                user = db.query(User).filter(User.id == souscription.user_id).first()
                if paiement and user:
                    try:
                        existing_definitive = AttestationService.create_attestation_definitive(
                            db=db,
                            souscription=souscription,
                            paiement=paiement,
                            user=user
                        )
                        definitive_created_this_request = True
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).exception(
                            "Erreur lors de la création de l'attestation définitive après validation production: %s", e
                        )

            if existing_definitive:
                # L'attestation définitive existe, vérifier si la carte numérique existe
                import logging
                logger = logging.getLogger(__name__)
                
                # Générer ou régénérer la carte :
                # - pas d'URL utilisable → générer ;
                # - attestation définitive existait déjà avant cette requête → régénérer (photo JSON/MinIO
                #   peut être arrivée après une 1re carte « placeholder », ou correctif backend).
                # - créée dans ce même appel avec une URL déjà posée par create_attestation_definitive → ne pas dupliquer.
                has_card_url = bool(
                    existing_definitive.carte_numerique_url
                    and len(str(existing_definitive.carte_numerique_url).strip()) > 0
                )
                card_needs_generation = (not has_card_url) or (not definitive_created_this_request)
                
                logger.info(
                    "🔍 Validation de production pour attestation %s (ID: %s): "
                    "carte_numerique_url=%s, carte_numerique_path=%s, carte_numerique_bucket=%s, "
                    "card_needs_generation=%s",
                    existing_definitive.numero_attestation,
                    existing_definitive.id,
                    "None" if not existing_definitive.carte_numerique_url else f"Present ({len(existing_definitive.carte_numerique_url)} chars)",
                    existing_definitive.carte_numerique_path or "None",
                    existing_definitive.carte_numerique_bucket or "None",
                    card_needs_generation
                )
                
                # TOUJOURS générer la carte si elle n'existe pas, même si path/bucket sont présents
                # Cela garantit que la carte est créée pour tous les parcours
                if card_needs_generation:
                    logger.info(
                        "🔄 DÉBUT de la génération de la carte pour l'attestation %s (ID: %s)",
                        existing_definitive.numero_attestation,
                        existing_definitive.id
                    )
                    # La carte n'existe pas ou n'a pas d'URL, la générer
                    logger.info(
                        "✅ Validation de production: Attestation définitive existante (ID: %s) sans carte numérique. Génération de la carte...",
                        existing_definitive.id
                    )
                    try:
                        # Générer la carte numérique pour l'attestation existante
                        from app.services.card_service import CardService
                        from app.services.minio_service import MinioService
                        from app.services.qrcode_service import QRCodeService
                        from base64 import b64encode
                        from io import BytesIO
                        
                        # Récupérer les données nécessaires
                        user = souscription.user
                        paiement = db.query(Paiement).filter(
                            Paiement.souscription_id == souscription.id
                        ).order_by(Paiement.created_at.desc()).first()
                        
                        if user and paiement:
                            logger.info(
                                "📸 Génération de la carte pour attestation %s: user=%s, paiement=%s",
                                existing_definitive.numero_attestation,
                                user.id if user else "None",
                                paiement.id if paiement else "None"
                            )
                            
                            # Générer le QR code
                            verification_url = AttestationService.build_verification_url(existing_definitive.numero_attestation)
                            qr_buffer = QRCodeService.generate_qr_image(verification_url)
                            qr_bytes = qr_buffer.getvalue()
                            logger.info("✅ QR code généré, taille: %d bytes", len(qr_bytes))
                            
                            # Extraire la photo d'identité
                            identity_photo = AttestationService._extract_identity_photo_bytes(db, souscription.id)
                            logger.info(
                                "📷 Photo d'identité extraite: %s (taille: %d bytes)",
                                "Oui" if identity_photo else "Non",
                                len(identity_photo) if identity_photo else 0
                            )
                            
                            # Extraire les informations du voyageur depuis le questionnaire administratif
                            traveler_info = AttestationService._extract_traveler_info(db, souscription.id)
                            
                            # Générer la carte
                            logger.info("🎨 Génération de l'image de la carte...")
                            card_buffer = CardService.generate_insurance_card(
                                user,
                                souscription,
                                existing_definitive.numero_attestation,
                                verification_url,
                                photo_bytes=identity_photo,
                                qr_bytes=qr_bytes,
                                traveler_info=traveler_info
                            )
                            card_bytes = card_buffer.getvalue()
                            logger.info("✅ Carte générée avec succès, taille: %d bytes", len(card_bytes))
                            
                            # Upload sur Minio
                            try:
                                card_path = MinioService.upload_card_image(
                                    card_bytes,
                                    souscription.id,
                                    existing_definitive.numero_attestation
                                )
                                card_bucket = MinioService.BUCKET_ATTESTATIONS
                                if _use_ecard_proxy_url():
                                    card_url = _build_ecard_proxy_url(existing_definitive.id)
                                    card_expires = datetime.utcnow() + timedelta(minutes=30)
                                else:
                                    card_url = MinioService.generate_signed_url(
                                        card_bucket,
                                        card_path,
                                        expires=timedelta(hours=24)
                                    )
                                    card_expires = datetime.utcnow() + timedelta(hours=24)
                                
                                # Mettre à jour l'attestation
                                existing_definitive.carte_numerique_path = card_path
                                existing_definitive.carte_numerique_bucket = card_bucket
                                existing_definitive.carte_numerique_url = card_url
                                existing_definitive.carte_numerique_expires_at = card_expires
                                
                                db.commit()
                                db.refresh(existing_definitive)
                                
                                logger.info(
                                    "Carte numérique générée avec succès pour l'attestation définitive %s (ID: %s) après validation de production",
                                    existing_definitive.numero_attestation,
                                    existing_definitive.id
                                )
                            except Exception as upload_error:
                                # Fallback: stockage inline si Minio échoue
                                logger.warning(
                                    "Échec de l'upload de la carte numérique sur Minio pour %s: %s. Utilisation du stockage inline.",
                                    existing_definitive.numero_attestation,
                                    upload_error
                                )
                                inline_payload = b64encode(card_bytes).decode("ascii")
                                card_url = f"data:image/png;base64,{inline_payload}"
                                existing_definitive.carte_numerique_path = INLINE_OBJECT_KEY
                                existing_definitive.carte_numerique_bucket = INLINE_BUCKET_NAME
                                existing_definitive.carte_numerique_url = card_url
                                existing_definitive.carte_numerique_expires_at = None
                                
                                db.commit()
                                db.refresh(existing_definitive)
                                
                                # Vérifier que l'URL a bien été sauvegardée
                                if not existing_definitive.carte_numerique_url:
                                    logger.error(
                                        "❌❌❌ PROBLÈME: La carte a été générée mais carte_numerique_url est toujours None après commit ! "
                                        "Attestation ID: %s, path: %s, bucket: %s",
                                        existing_definitive.id,
                                        existing_definitive.carte_numerique_path,
                                        existing_definitive.carte_numerique_bucket
                                    )
                                else:
                                    logger.info(
                                        "✅ Vérification post-commit: carte_numerique_url est présent (%d caractères)",
                                        len(existing_definitive.carte_numerique_url)
                                    )
                        else:
                            logger.error(
                                "❌ Impossible de générer la carte: user ou paiement manquant. "
                                "user=%s, paiement=%s, souscription_id=%s",
                                "Present" if user else "None",
                                "Present" if paiement else "None",
                                souscription.id
                            )
                    except Exception as card_error:
                        import traceback
                        logger.error(
                            "❌❌❌ ERREUR lors de la génération de la carte numérique pour l'attestation définitive %s (ID: %s) après validation de production: %s\nTraceback: %s",
                            existing_definitive.numero_attestation,
                            existing_definitive.id,
                            str(card_error),
                            traceback.format_exc()
                        )
                        # Ne pas bloquer la validation si la génération de la carte échoue
    except Exception as production_err:
        import logging
        logging.getLogger(__name__).exception(
            "Erreur bloc production (attestation définitive / carte) pour attestation_id=%s: %s",
            attestation_id,
            production_err,
        )

    # Si toutes les validations sont complètes et que c'est une attestation provisoire,
    # générer l'attestation définitive
    if attestation.type_attestation == "provisoire" and validation.est_valide:
        if AttestationService.check_all_validations_complete(db, attestation):
            # Vérifier si une attestation définitive existe déjà
            existing_definitive = db.query(Attestation).filter(
                Attestation.souscription_id == souscription.id,
                Attestation.type_attestation == "definitive"
            ).first()
            
            if not existing_definitive:
                # Générer l'attestation définitive
                paiement = db.query(Paiement).filter(
                    Paiement.id == attestation.paiement_id
                ).first() if attestation.paiement_id else None
                
                if souscription and paiement:
                    from app.models.user import User
                    user = db.query(User).filter(User.id == souscription.user_id).first()
                    if user:
                        try:
                            attestation_definitive = AttestationService.create_attestation_definitive(
                                db=db,
                                souscription=souscription,
                                paiement=paiement,
                                user=user
                            )
                            # Le commit est déjà fait dans create_attestation_definitive
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(
                                "Attestation définitive créée avec succès: %s (ID: %s). Carte numérique: %s",
                                attestation_definitive.numero_attestation,
                                attestation_definitive.id,
                                "Oui" if attestation_definitive.carte_numerique_url else "Non"
                            )
                        except Exception as e:
                            import logging
                            import traceback
                            logger = logging.getLogger(__name__)
                            logger.error(
                                "Erreur lors de la création de l'attestation définitive pour la souscription %s: %s\nTraceback: %s",
                                souscription.id,
                                str(e),
                                traceback.format_exc()
                            )
                            # Ne pas bloquer la validation si l'attestation échoue
                            # L'admin pourra la générer manuellement
            else:
                # L'attestation définitive existait déjà avant ce flux : régénérer la e-carte pour appliquer
                # la photo à jour (sinon une ancienne PNG avec placeholder reste servie tant que l'URL existe).
                import logging
                logger = logging.getLogger(__name__)
                
                card_needs_generation = True
                
                if card_needs_generation:
                    logger.info(
                        "Attestation définitive existante (ID: %s). Régénération de la carte numérique (photo / correctifs)...",
                        existing_definitive.id
                    )
                    try:
                        # Générer la carte numérique pour l'attestation existante
                        from app.services.card_service import CardService
                        from app.services.minio_service import MinioService
                        from app.services.qrcode_service import QRCodeService
                        from base64 import b64encode
                        from io import BytesIO
                        
                        # Récupérer les données nécessaires
                        user = souscription.user
                        paiement = db.query(Paiement).filter(
                            Paiement.souscription_id == souscription.id
                        ).order_by(Paiement.created_at.desc()).first()
                        
                        if user and paiement:
                            # Générer le QR code
                            verification_url = AttestationService.build_verification_url(existing_definitive.numero_attestation)
                            qr_buffer = QRCodeService.generate_qr_image(verification_url)
                            qr_bytes = qr_buffer.getvalue()
                            
                            # Extraire la photo d'identité
                            identity_photo = AttestationService._extract_identity_photo_bytes(db, souscription.id)
                            
                            # Extraire les informations du voyageur depuis le questionnaire administratif
                            traveler_info = AttestationService._extract_traveler_info(db, souscription.id)
                            
                            # Générer la carte
                            card_buffer = CardService.generate_insurance_card(
                                user,
                                souscription,
                                existing_definitive.numero_attestation,
                                verification_url,
                                photo_bytes=identity_photo,
                                qr_bytes=qr_bytes,
                                traveler_info=traveler_info
                            )
                            card_bytes = card_buffer.getvalue()
                            
                            # Upload sur Minio
                            try:
                                card_path = MinioService.upload_card_image(
                                    card_bytes,
                                    souscription.id,
                                    existing_definitive.numero_attestation
                                )
                                card_bucket = MinioService.BUCKET_ATTESTATIONS
                                if _use_ecard_proxy_url():
                                    card_url = _build_ecard_proxy_url(existing_definitive.id)
                                    card_expires = datetime.utcnow() + timedelta(minutes=30)
                                else:
                                    card_url = MinioService.generate_signed_url(
                                        card_bucket,
                                        card_path,
                                        expires=timedelta(hours=24)
                                    )
                                    card_expires = datetime.utcnow() + timedelta(hours=24)
                                
                                # Mettre à jour l'attestation
                                existing_definitive.carte_numerique_path = card_path
                                existing_definitive.carte_numerique_bucket = card_bucket
                                existing_definitive.carte_numerique_url = card_url
                                existing_definitive.carte_numerique_expires_at = card_expires
                                
                                db.commit()
                                db.refresh(existing_definitive)
                                
                                logger.info(
                                    "Carte numérique générée avec succès pour l'attestation définitive %s (ID: %s)",
                                    existing_definitive.numero_attestation,
                                    existing_definitive.id
                                )
                            except Exception as upload_error:
                                # Fallback: stockage inline si Minio échoue
                                logger.warning(
                                    "Échec de l'upload de la carte numérique sur Minio pour %s: %s. Utilisation du stockage inline.",
                                    existing_definitive.numero_attestation,
                                    upload_error
                                )
                                inline_payload = b64encode(card_bytes).decode("ascii")
                                card_url = f"data:image/png;base64,{inline_payload}"
                                existing_definitive.carte_numerique_path = INLINE_OBJECT_KEY
                                existing_definitive.carte_numerique_bucket = INLINE_BUCKET_NAME
                                existing_definitive.carte_numerique_url = card_url
                                existing_definitive.carte_numerique_expires_at = None
                                
                                db.commit()
                                db.refresh(existing_definitive)
                    except Exception as card_error:
                        import traceback
                        logger.error(
                            "Erreur lors de la génération de la carte numérique pour l'attestation définitive %s (ID: %s): %s\nTraceback: %s",
                            existing_definitive.numero_attestation,
                            existing_definitive.id,
                            str(card_error),
                            traceback.format_exc()
                        )
                        # Ne pas bloquer la validation si la génération de la carte échoue
    
    db.commit()
    db.refresh(validation_obj)
    return validation_obj


@router.get("/attestations/{attestation_id}/validations", response_model=List[ValidationAttestationResponse])
async def get_attestation_validations(
    attestation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir toutes les validations d'une attestation"""
    # Vérifier que l'attestation existe
    attestation = db.query(Attestation).filter(
        Attestation.id == attestation_id
    ).first()
    
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation non trouvée"
        )
    
    # Vérifier les permissions (utilisateur propriétaire ou admin/doctor)
    souscription = db.query(Souscription).filter(
        Souscription.id == attestation.souscription_id
    ).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    reviewer_roles = {
        Role.ADMIN,
        Role.DOCTOR,
        Role.HOSPITAL_ADMIN,
        Role.MEDICAL_REVIEWER,
        Role.TECHNICAL_REVIEWER,
        Role.PRODUCTION_AGENT,
    }
    if souscription.user_id != current_user.id and current_user.role not in reviewer_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    validations = db.query(ValidationAttestation).filter(
        ValidationAttestation.attestation_id == attestation_id
    ).all()
    
    return validations


@router.get("/attestations/verify/{numero_attestation}", response_model=AttestationVerificationResponse)
async def verify_attestation(
    numero_attestation: str,
    db: Session = Depends(get_db)
):
    """Vérifier publiquement la validité d'une attestation via son numéro (utilisé par le QR code)."""
    attestation = db.query(Attestation).filter(
        Attestation.numero_attestation == numero_attestation
    ).first()

    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation non trouvée"
        )

    souscription = db.query(Souscription).filter(
        Souscription.id == attestation.souscription_id
    ).first()

    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription associée introuvable"
        )

    if not attestation.est_valide:
        message = "Cette attestation a été annulée."
    elif attestation.type_attestation == "provisoire":
        message = "Attestation provisoire valide. En attente de validations complémentaires."
    else:
        message = "Attestation définitive validée."

    return AttestationVerificationResponse(
        numero_attestation=attestation.numero_attestation,
        type_attestation=attestation.type_attestation,
        est_valide=attestation.est_valide,
        souscription_numero=souscription.numero_souscription,
        statut_souscription=souscription.statut.value if hasattr(souscription.statut, "value") else souscription.statut,
        message=message,
        created_at=attestation.created_at
    )

