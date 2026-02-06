from datetime import datetime, timedelta, date
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.enums import StatutSouscription, Role, StatutPaiement
from app.api.v1.auth import get_current_user, require_admin_user
from app.models.user import User
from app.models.souscription import Souscription
from app.models.produit_assurance import ProduitAssurance
from app.models.projet_voyage import ProjetVoyage
from app.models.attestation import Attestation
from app.models.paiement import Paiement
from app.models.finance_account import Account
from app.schemas.souscription import SouscriptionResponse
from app.schemas.ecard import ECardResponse
from app.services.attestation_service import AttestationService
from app.services.finance_service import FinanceService
from app.services.prime_tarif_service import resolve_prime_tarif
from pydantic import BaseModel
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _age_from_birthdate(birthdate: Optional[date]) -> Optional[int]:
    """Calcule l'âge en années à partir de la date de naissance."""
    if not birthdate:
        return None
    today = date.today()
    return (today - birthdate).days // 365


def require_production_agent(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a production agent or admin"""
    if current_user.role not in {Role.PRODUCTION_AGENT, Role.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Production agent or admin role required."
        )
    return current_user


class SouscriptionStartRequest(BaseModel):
    """Schéma pour démarrer une souscription"""
    produit_assurance_id: int
    projet_voyage_id: Optional[int] = None
    date_debut: Optional[datetime] = None
    notes: Optional[str] = None
    user_id: Optional[int] = None  # ID de l'utilisateur pour qui on souscrit (pour souscription pour un tiers)
    # Caractéristiques pour tarif selon durée, zone et âge (sinon prix de base)
    destination_country_id: Optional[int] = None
    zone_code: Optional[str] = None
    duree_jours: Optional[int] = None
    age: Optional[int] = None  # Si absent, calculé depuis l'utilisateur cible (date_naissance)


@router.post("/start", response_model=SouscriptionResponse, status_code=status.HTTP_201_CREATED)
async def start_subscription(
    subscription_data: SouscriptionStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Démarrer une nouvelle souscription en statut 'pending' (en_attente).
    Le prix est automatiquement calculé à partir du produit d'assurance.
    
    Si user_id est fourni, permet de souscrire pour un tiers (nécessite les permissions ADMIN ou PRODUCTION_AGENT).
    Sinon, la souscription est créée pour l'utilisateur connecté.
    """
    # Déterminer l'utilisateur pour qui on souscrit
    target_user_id = subscription_data.user_id if subscription_data.user_id else current_user.id
    
    # Si on essaie de souscrire pour un tiers, vérifier les permissions
    if subscription_data.user_id and subscription_data.user_id != current_user.id:
        # Vérifier que l'utilisateur actuel a les permissions pour souscrire pour un tiers
        if current_user.role not in {Role.ADMIN, Role.PRODUCTION_AGENT}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas les permissions pour souscrire pour un tiers. Rôles autorisés: ADMIN, PRODUCTION_AGENT"
            )
        
        # Vérifier que l'utilisateur cible existe
        target_user = db.query(User).filter(User.id == subscription_data.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Utilisateur avec l'ID {subscription_data.user_id} non trouvé"
            )
    
    # Vérifier que le produit existe et est actif
    produit = db.query(ProduitAssurance).filter(
        ProduitAssurance.id == subscription_data.produit_assurance_id,
        ProduitAssurance.est_actif == True
    ).first()
    
    if not produit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit d'assurance non trouvé ou inactif"
        )
    
    # Vérifier le projet de voyage si fourni
    projet = None
    if subscription_data.projet_voyage_id:
        projet = db.query(ProjetVoyage).filter(
            ProjetVoyage.id == subscription_data.projet_voyage_id
        ).first()
        
        if not projet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projet de voyage non trouvé"
            )
        
        # Vérifier que le projet appartient à l'utilisateur cible (ou à l'utilisateur actuel si souscription pour soi)
        if projet.user_id != target_user_id:
            # Si l'utilisateur actuel a les permissions, on peut accepter même si le projet n'appartient pas à l'utilisateur cible
            if current_user.role not in {Role.ADMIN, Role.PRODUCTION_AGENT}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Ce projet de voyage ne vous appartient pas"
                )
            # Si on a les permissions mais que le projet n'appartient pas à l'utilisateur cible, on avertit mais on continue
            logger.warning(
                f"Projet de voyage {projet.id} appartient à l'utilisateur {projet.user_id} "
                f"mais souscription créée pour l'utilisateur {target_user_id} par {current_user.id}"
            )
    
    # Âge : depuis la requête ou l'utilisateur cible (date_naissance)
    target_user = db.query(User).filter(User.id == target_user_id).first()
    age = subscription_data.age
    if age is None and target_user and getattr(target_user, "date_naissance", None):
        age = _age_from_birthdate(target_user.date_naissance)
    
    # Durée et zone : depuis la requête ou le projet
    duree_jours = subscription_data.duree_jours
    destination_country_id = subscription_data.destination_country_id
    zone_code = subscription_data.zone_code
    if projet:
        if duree_jours is None and projet.date_depart and projet.date_retour:
            delta = projet.date_retour - projet.date_depart
            duree_jours = max(0, delta.days)
        if destination_country_id is None and getattr(projet, "destination_country_id", None) is not None:
            destination_country_id = projet.destination_country_id
    
    # Tarif selon durée, zone et âge ; sinon prix de base
    prix_applique, *_ = resolve_prime_tarif(
        db,
        product_id=produit.id,
        age=age,
        destination_country_id=destination_country_id,
        zone_code=zone_code,
        duree_jours=duree_jours,
    )
    
    # Déterminer la date de début
    date_debut = subscription_data.date_debut
    if not date_debut:
        if projet:
            date_debut = projet.date_depart
        else:
            date_debut = datetime.utcnow()
    
    # Déterminer la date de fin
    date_fin = None
    if produit.duree_validite_jours:
        date_fin = date_debut + timedelta(days=produit.duree_validite_jours)
    elif projet and projet.date_retour:
        date_fin = projet.date_retour
    
    # Générer un numéro de souscription unique
    numero_souscription = f"SUB-{uuid.uuid4().hex[:8].upper()}-{datetime.utcnow().strftime('%Y%m%d')}"
    
    # Vérifier l'unicité du numéro (très peu probable mais on vérifie)
    existing = db.query(Souscription).filter(
        Souscription.numero_souscription == numero_souscription
    ).first()
    if existing:
        numero_souscription = f"SUB-{uuid.uuid4().hex[:8].upper()}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Créer la souscription
    souscription = Souscription(
        user_id=target_user_id,  # Utiliser l'ID de l'utilisateur cible
        produit_assurance_id=subscription_data.produit_assurance_id,
        projet_voyage_id=subscription_data.projet_voyage_id,
        numero_souscription=numero_souscription,
        prix_applique=prix_applique,  # Prix calculé automatiquement
        date_debut=date_debut,
        date_fin=date_fin,
        statut=StatutSouscription.EN_ATTENTE,  # Statut 'pending' (en_attente)
        notes=subscription_data.notes
    )
    
    db.add(souscription)
    db.commit()
    db.refresh(souscription)
    # Précharger les relations nécessaires pour la réponse
    souscription.produit_assurance = produit
    if projet:
        souscription.projet_voyage = projet
    
    return souscription


async def _get_subscriptions_impl(
    skip: int = 0,
    limit: int = 100,
    db: Session = None,
    current_user: User = None
):
    """Implémentation commune pour récupérer les souscriptions"""
    logger.info(f"Récupération des souscriptions pour l'utilisateur {current_user.id} (username: {current_user.username}, email: {current_user.email})")
    logger.info(f"Paramètres: skip={skip}, limit={limit}")
    
    # Compter le total de souscriptions pour cet utilisateur (sans limite)
    total_count = db.query(Souscription).filter(
        Souscription.user_id == current_user.id
    ).count()
    logger.info(f"Nombre total de souscriptions pour l'utilisateur {current_user.id}: {total_count}")
    
    souscriptions = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
        )
        .filter(Souscription.user_id == current_user.id)
        .order_by(Souscription.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    logger.info(f"Nombre de souscriptions retournées: {len(souscriptions)}")
    if souscriptions:
        logger.info(f"Statuts des souscriptions retournées: {[s.statut for s in souscriptions]}")
        logger.info(f"IDs des souscriptions: {[s.id for s in souscriptions]}")
    
    return souscriptions


@router.get("/", response_model=List[SouscriptionResponse])
async def get_subscriptions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la liste des souscriptions de l'utilisateur (avec slash)"""
    return await _get_subscriptions_impl(skip=skip, limit=limit, db=db, current_user=current_user)


@router.get("", response_model=List[SouscriptionResponse], include_in_schema=False)
async def get_subscriptions_no_slash(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la liste des souscriptions de l'utilisateur (sans slash - pour compatibilité mobile)"""
    return await _get_subscriptions_impl(skip=skip, limit=limit, db=db, current_user=current_user)


@router.get("/pending-resiliations", response_model=List[SouscriptionResponse])
async def get_pending_resiliations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_production_agent)
):
    """Obtenir la liste des souscriptions avec des demandes de résiliation en attente"""
    souscriptions = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
            selectinload(Souscription.user),
        )
        .filter(Souscription.demande_resiliation == "pending")
        .order_by(Souscription.demande_resiliation_date.desc())
        .all()
    )
    
    return souscriptions


@router.get("/{subscription_id}/user-photo")
async def get_subscription_user_photo(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la photo d'identité de l'utilisateur depuis le questionnaire administratif de la souscription"""
    from app.models.questionnaire import Questionnaire
    
    # Vérifier que la souscription existe
    souscription = db.query(Souscription).filter(
        Souscription.id == subscription_id
    ).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier les permissions (utilisateur propriétaire ou rôles autorisés)
    allowed_roles = [
        Role.ADMIN,
        Role.SOS_OPERATOR,
        Role.DOCTOR,
        Role.MEDICAL_REVIEWER,
        Role.TECHNICAL_REVIEWER,
        Role.PRODUCTION_AGENT,
        Role.AGENT_SINISTRE_MH,
    ]
    if souscription.user_id != current_user.id and current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    # Récupérer le questionnaire administratif le plus récent
    questionnaire = (
        db.query(Questionnaire)
        .filter(
            Questionnaire.souscription_id == subscription_id,
            Questionnaire.type_questionnaire == "administratif",
        )
        .order_by(Questionnaire.version.desc())
        .first()
    )
    
    if not questionnaire or not questionnaire.reponses:
        return {"photo_url": None}
    
    # Chercher la photo dans différents emplacements possibles
    personal = questionnaire.reponses.get("personal") or {}
    technical = questionnaire.reponses.get("technical") or {}
    
    photo_payload = (
        personal.get("photoIdentity") or 
        personal.get("photo_identity") or
        technical.get("photoIdentity") or
        technical.get("photo_identity") or
        questionnaire.reponses.get("photoIdentity") or
        questionnaire.reponses.get("photo_identity") or
        questionnaire.reponses.get("identityPhoto") or
        questionnaire.reponses.get("identity_photo")
    )
    
    if not photo_payload:
        return {"photo_url": None}
    
    # Extraire l'URL de la photo (peut être une data URL ou une URL signée)
    photo_url = None
    if isinstance(photo_payload, str):
        # Si c'est une chaîne, c'est probablement une data URL ou une URL
        photo_url = photo_payload
    elif isinstance(photo_payload, dict):
        # Si c'est un objet, chercher dataUrl, url, ou photo_url
        photo_url = (
            photo_payload.get("dataUrl") or
            photo_payload.get("url") or
            photo_payload.get("photo_url") or
            photo_payload.get("base64")  # Si c'est juste le base64, on peut le convertir en data URL
        )
        # Si on a seulement le base64, créer une data URL
        if not photo_url and photo_payload.get("base64"):
            photo_url = f"data:image/jpeg;base64,{photo_payload.get('base64')}"
    
    return {"photo_url": photo_url}


@router.get("/{subscription_id}", response_model=SouscriptionResponse)
async def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir une souscription par ID"""
    souscription = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
        )
        .filter(
            Souscription.id == subscription_id,
            Souscription.user_id == current_user.id
        )
        .first()
    )
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    return souscription


@router.get("/{subscription_id}/ecard", response_model=ECardResponse)
async def get_subscription_ecard(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourner la carte numérique associée à une souscription active."""
    souscription = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.user),
            selectinload(Souscription.produit_assurance),
        )
        .filter(
            Souscription.id == subscription_id,
            Souscription.user_id == current_user.id,
        )
        .first()
    )

    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée",
        )

    attestation = (
        db.query(Attestation)
        .filter(
            Attestation.souscription_id == subscription_id,
            Attestation.type_attestation == "definitive",
            Attestation.est_valide == True,  # noqa: E712 - SQLAlchemy convention
        )
        .order_by(Attestation.created_at.desc())
        .first()
    )

    if not attestation or not attestation.carte_numerique_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune carte numérique disponible pour cette souscription",
        )

    needs_refresh = (
        attestation.carte_numerique_path
        and attestation.carte_numerique_bucket
        and (
            not attestation.carte_numerique_expires_at
            or attestation.carte_numerique_expires_at
            <= datetime.utcnow() + timedelta(minutes=5)
        )
    )

    if needs_refresh:
        AttestationService.refresh_signed_url(
            db=db,
            attestation=attestation,
            expires=timedelta(hours=1),
            refresh_card=True,
        )
        db.refresh(attestation)

    # Extraire les informations du voyageur depuis le questionnaire administratif
    traveler_info = AttestationService._extract_traveler_info(db, souscription.id)
    
    # Utiliser les informations du voyageur si disponibles, sinon fallback sur l'utilisateur
    if traveler_info and traveler_info.get("fullName"):
        holder_name = traveler_info.get("fullName", "")
    else:
        user_obj = getattr(souscription, "user", None)
        if user_obj:
            holder_name = (
                user_obj.full_name
                or user_obj.username
                or user_obj.email
                or "Assuré(e)"
            )
        else:
            holder_name = "Assuré(e)"

    return ECardResponse(
        subscription_id=souscription.id,
        numero_souscription=souscription.numero_souscription,
        holder_name=holder_name,
        card_url=attestation.carte_numerique_url,
        card_expires_at=attestation.carte_numerique_expires_at,
        coverage_end_date=souscription.date_fin,
        generated_at=attestation.created_at,
    )


@router.get("/{subscription_id}/ecard/download")
async def download_subscription_ecard(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Télécharger directement la carte numérique depuis Minio (évite les problèmes d'URL signée)"""
    souscription = (
        db.query(Souscription)
        .filter(
            Souscription.id == subscription_id,
            Souscription.user_id == current_user.id,
        )
        .first()
    )

    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée",
        )

    attestation = (
        db.query(Attestation)
        .filter(
            Attestation.souscription_id == subscription_id,
            Attestation.type_attestation == "definitive",
            Attestation.est_valide == True,  # noqa: E712 - SQLAlchemy convention
        )
        .order_by(Attestation.created_at.desc())
        .first()
    )

    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune attestation définitive trouvée pour cette souscription",
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
                    f"(Souscription ID: {subscription_id}, Attestation ID: {attestation.id})"
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


class ResiliationRequest(BaseModel):
    """Schéma pour demander la résiliation d'une souscription"""
    notes: Optional[str] = None


class ResiliationDecisionRequest(BaseModel):
    """Schéma pour valider ou refuser une demande de résiliation"""
    approved: bool
    notes: Optional[str] = None


@router.post("/{subscription_id}/request-resiliation", response_model=SouscriptionResponse)
async def request_resiliation(
    subscription_id: int,
    request: ResiliationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Demander la résiliation d'une souscription"""
    souscription = (
        db.query(Souscription)
        .filter(
            Souscription.id == subscription_id,
            Souscription.user_id == current_user.id
        )
        .first()
    )
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier que la souscription est active
    if souscription.statut != StatutSouscription.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les souscriptions actives peuvent être résiliées"
        )
    
    # Vérifier qu'il n'y a pas déjà une demande en cours
    if souscription.demande_resiliation == "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une demande de résiliation est déjà en cours"
        )
    
    # Créer la demande de résiliation
    souscription.demande_resiliation = "pending"
    souscription.demande_resiliation_date = datetime.utcnow()
    souscription.demande_resiliation_notes = request.notes
    
    db.commit()
    db.refresh(souscription)
    
    return souscription


@router.post("/{subscription_id}/process-resiliation", response_model=SouscriptionResponse)
async def process_resiliation(
    subscription_id: int,
    decision: ResiliationDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_production_agent)
):
    """Valider ou refuser une demande de résiliation (agent de production)"""
    souscription = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
        )
        .filter(Souscription.id == subscription_id)
        .first()
    )
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier qu'il y a une demande en cours
    if souscription.demande_resiliation != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune demande de résiliation en cours"
        )
    
    # Traiter la demande
    souscription.demande_resiliation = "approved" if decision.approved else "rejected"
    souscription.demande_resiliation_par_agent = current_user.id
    souscription.demande_resiliation_date_traitement = datetime.utcnow()
    if decision.notes:
        souscription.demande_resiliation_notes = (
            (souscription.demande_resiliation_notes or "") + "\n\n" + decision.notes
        ).strip()
    
    # Si approuvé, marquer la souscription comme résiliée et créer un remboursement de 50%
    if decision.approved:
        souscription.statut = StatutSouscription.RESILIEE
        souscription.date_fin = datetime.utcnow()
        
        # Créer un remboursement de 50% du montant de souscription
        try:
            # Trouver le paiement associé à la souscription
            paiement = (
                db.query(Paiement)
                .filter(Paiement.souscription_id == souscription.id)
                .filter(Paiement.statut == StatutPaiement.VALIDE)
                .order_by(Paiement.created_at.desc())
                .first()
            )
            
            if paiement:
                # Calculer le montant du remboursement (50% du prix de souscription)
                montant_remboursement = (souscription.prix_applique * Decimal("0.50")).quantize(Decimal("0.01"))
                
                # Trouver ou créer le compte financier du client
                account = (
                    db.query(Account)
                    .filter(Account.owner_id == souscription.user_id)
                    .filter(Account.account_type == "client")
                    .first()
                )
                
                if not account:
                    # Créer un compte client si il n'existe pas
                    account_number = f"CLIENT-{souscription.user_id}-{uuid.uuid4().hex[:8].upper()}"
                    account = Account(
                        account_number=account_number,
                        account_name=f"Compte client - {souscription.user_id}",
                        account_type="client",
                        balance=Decimal("0.00"),
                        currency="EUR",
                        is_active=True,
                        owner_id=souscription.user_id
                    )
                    db.add(account)
                    db.flush()  # Pour obtenir l'ID du compte
                    logger.info(f"Created client account {account.id} for user {souscription.user_id}")
                
                # Créer le remboursement via le service
                raison = f"Résiliation de la souscription {souscription.numero_souscription or souscription.id}"
                if decision.notes:
                    raison += f" - {decision.notes}"
                
                FinanceService.process_refund(
                    db=db,
                    paiement_id=paiement.id,
                    account_id=account.id,
                    montant=montant_remboursement,
                    raison=raison,
                    processed_by=current_user.id
                )
                
                logger.info(f"Refund created for subscription {souscription.id}: {montant_remboursement} EUR (50% of {souscription.prix_applique})")
            else:
                logger.warning(f"No valid payment found for subscription {souscription.id}, skipping refund")
        except Exception as e:
            logger.error(f"Error creating refund for subscription {souscription.id}: {e}", exc_info=True)
            # Ne pas bloquer la résiliation si le remboursement échoue
            # On continue quand même avec la résiliation
    
    db.commit()
    db.refresh(souscription)
    
    return souscription


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une souscription résiliée"""
    souscription = (
        db.query(Souscription)
        .filter(
            Souscription.id == subscription_id,
            Souscription.user_id == current_user.id
        )
        .first()
    )
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier que la souscription est résiliée
    if souscription.statut != StatutSouscription.RESILIEE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les souscriptions résiliées peuvent être supprimées"
        )
    
    # Supprimer la souscription (les attestations seront supprimées en cascade)
    db.delete(souscription)
    db.commit()
    
    return None