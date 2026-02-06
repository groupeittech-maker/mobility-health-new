import logging
from typing import List, Optional
from datetime import timedelta
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.souscription import Souscription
from app.models.attestation import Attestation
from app.models.paiement import Paiement
from app.models.invoice import Invoice
from app.schemas.attestation import AttestationResponse
from app.services.attestation_service import AttestationService
from pydantic import BaseModel
from datetime import datetime
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)


def _stream_from_url_as_pdf(url: str, filename: str) -> StreamingResponse:
    """
    Récupère le fichier depuis une URL (ex. Minio presignée) côté serveur
    et le renvoie au client en stream. Évite d'envoyer une redirection vers
    localhost:9000 au téléphone (qui ne peut pas joindre Minio).
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content = resp.content
    except Exception as e:
        logger.warning(f"Échec récupération fichier depuis URL (stream): {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Impossible de récupérer le fichier. Réessayez plus tard."
        )
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


class DocumentResponse(BaseModel):
    """Réponse générique pour un document"""
    id: int
    type: str  # 'attestation_provisoire', 'attestation_definitive', 'facture', 'recu', 'justificatif'
    titre: str
    numero: str
    date_creation: datetime
    url_download: Optional[str] = None
    souscription_id: Optional[int] = None
    paiement_id: Optional[int] = None
    
    class Config:
        from_attributes = False


@router.get("/documents", response_model=List[DocumentResponse])
async def get_user_documents(
    subscription_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtenir tous les documents de l'utilisateur (attestations, factures, reçus)
    Optionnellement filtrer par souscription
    """
    documents = []
    
    # Récupérer les souscriptions de l'utilisateur
    query = db.query(Souscription).filter(Souscription.user_id == current_user.id)
    if subscription_id:
        query = query.filter(Souscription.id == subscription_id)
    
    souscriptions = query.all()
    
    # Récupérer les attestations
    for souscription in souscriptions:
        attestations = db.query(Attestation).filter(
            Attestation.souscription_id == souscription.id,
            Attestation.est_valide == True
        ).order_by(Attestation.created_at.desc()).all()
        
        for attestation in attestations:
            # Générer une URL fraîche à la volée à partir de la clé stockée
            from app.services.minio_service import MinioService
            from app.services.attestation_service import INLINE_BUCKET_NAME, INLINE_OBJECT_KEY
            
            url_signee = None
            uses_inline_storage = attestation.bucket_minio == INLINE_BUCKET_NAME or \
                attestation.chemin_fichier_minio == INLINE_OBJECT_KEY
            
            if not uses_inline_storage and attestation.chemin_fichier_minio:
                try:
                    # TOUJOURS régénérer l'URL (ignorer celle stockée en base)
                    url_signee = MinioService.get_pdf_url(
                        attestation.chemin_fichier_minio,
                        attestation.bucket_minio,
                        timedelta(hours=24)  # 24h d'expiration (au lieu de 2h)
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
                                timedelta(hours=2)
                            )
                            logger.info(f"URL régénérée avec succès pour l'attestation {attestation.id}")
                        except Exception as retry_error:
                            logger.error(
                                f"Échec de la régénération de l'URL pour l'attestation {attestation.id}: {retry_error}"
                            )
                            url_signee = attestation.url_signee
                    else:
                        logger.error(f"Erreur lors de la génération de l'URL pour l'attestation {attestation.id}: {e}")
                        url_signee = attestation.url_signee
                else:
                    # Pour le stockage inline, utiliser l'URL stockée (data URI)
                    url_signee = attestation.url_signee
            
            doc_type = 'attestation_provisoire' if attestation.type_attestation == 'provisoire' else 'attestation_definitive'
            titre = f"Attestation {'Provisoire' if attestation.type_attestation == 'provisoire' else 'Définitive'}"
            
            documents.append(DocumentResponse(
                id=attestation.id,
                type=doc_type,
                titre=titre,
                numero=attestation.numero_attestation,
                date_creation=attestation.created_at,
                url_download=url_signee,
                souscription_id=attestation.souscription_id,
                paiement_id=attestation.paiement_id
            ))
    
    # Récupérer les paiements (pour les reçus)
    for souscription in souscriptions:
        from app.core.enums import StatutPaiement
        paiements = db.query(Paiement).filter(
            Paiement.souscription_id == souscription.id,
            Paiement.statut == StatutPaiement.VALIDE
        ).order_by(Paiement.created_at.desc()).all()
        
        for paiement in paiements:
            # Créer un "reçu" basé sur le paiement
            # En production, on pourrait générer un PDF de reçu
            documents.append(DocumentResponse(
                id=paiement.id,
                type='recu',
                titre='Reçu de paiement',
                numero=paiement.reference_transaction or f"RECU-{paiement.id}",
                date_creation=paiement.date_paiement or paiement.created_at,
                url_download=None,  # À implémenter : génération de PDF de reçu
                souscription_id=paiement.souscription_id,
                paiement_id=paiement.id
            ))
    
    # Récupérer les factures (si l'utilisateur est un hôpital ou a des factures liées)
    # Pour l'instant, on se concentre sur les factures liées aux souscriptions via les paiements
    # Les factures d'hôpitaux sont gérées séparément
    
    # Trier par date de création (plus récent en premier)
    documents.sort(key=lambda x: x.date_creation, reverse=True)
    
    return documents


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    document_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Télécharger un document spécifique
    document_type: 'attestation_provisoire', 'attestation_definitive', 'facture', 'recu'
    """
    if document_type.startswith('attestation_'):
        # Récupérer l'attestation
        attestation = db.query(Attestation).filter(Attestation.id == document_id).first()
        
        if not attestation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )
        
        # Vérifier les permissions
        souscription = db.query(Souscription).filter(
            Souscription.id == attestation.souscription_id
        ).first()
        
        if not souscription or souscription.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé"
            )
        
        # Récupérer le fichier directement depuis Minio et le servir
        from app.services.minio_service import MinioService
        
        # Vérifier que le fichier existe dans Minio
        if not attestation.chemin_fichier_minio or attestation.chemin_fichier_minio == "INLINE_PDF":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier non disponible (stockage inline)"
            )
        
        bucket_name = attestation.bucket_minio or MinioService.BUCKET_ATTESTATIONS
        
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
                        f"Fichier non trouvé dans MinIO: {bucket_name}/{attestation.chemin_fichier_minio} "
                        f"(Attestation ID: {attestation.id}, Numéro: {attestation.numero_attestation})"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Le fichier PDF n'existe pas dans le stockage. "
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
                    "Content-Disposition": f'attachment; filename="{attestation.numero_attestation}.pdf"'
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
            
            # Vérifier si c'est une erreur d'URL expirée
            is_expired = MinioService.is_expired_url_error(s3_error)
            
            if is_expired:
                logger.warning(
                    f"URL expirée détectée lors de la récupération du fichier "
                    f"{bucket_name}/{attestation.chemin_fichier_minio}. "
                    f"Régénération de l'URL... ({error_info})"
                )
            else:
                logger.error(
                    f"Erreur MinIO lors de la récupération du fichier "
                    f"{bucket_name}/{attestation.chemin_fichier_minio}. "
                    f"{error_info}",
                    exc_info=True
                )
            
            # Fallback : récupérer le fichier via l'URL signée côté serveur et le streamer
            # (évite d'envoyer une redirection vers Minio localhost:9000 au téléphone)
            try:
                url_signee = AttestationService.refresh_signed_url(
                    db=db,
                    attestation=attestation,
                    expires=timedelta(hours=1)
                )
                logger.info("URL régénérée, stream du fichier depuis le serveur (pas de redirection).")
                return _stream_from_url_as_pdf(url_signee, f"{attestation.numero_attestation}.pdf")
            except Exception as fallback_error:
                logger.error(f"Erreur lors du fallback vers URL signée: {fallback_error}")
                if is_expired:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="L'URL du fichier a expiré et n'a pas pu être régénérée. "
                               "Vérifiez la synchronisation de l'heure du serveur. "
                               f"Erreur: {error_info}"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Impossible d'accéder au fichier. Erreur MinIO: {error_info}"
                    )
        except Exception as e:
            # En cas d'erreur, fallback : stream depuis l'URL signée (côté serveur, pas de redirection)
            logger.warning(
                f"Erreur lors de la récupération directe depuis Minio: {str(e)}, "
                f"fallback vers stream depuis URL signée",
                exc_info=True
            )
            
            try:
                url_signee = AttestationService.refresh_signed_url(
                    db=db,
                    attestation=attestation,
                    expires=timedelta(hours=1)
                )
                return _stream_from_url_as_pdf(url_signee, f"{attestation.numero_attestation}.pdf")
            except Exception as fallback_error:
                logger.error(f"Erreur lors du fallback vers URL signée: {fallback_error}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Impossible d'accéder au fichier: {str(e)}"
                )
    
    elif document_type == 'recu':
        # Récupérer le paiement
        paiement = db.query(Paiement).filter(Paiement.id == document_id).first()
        
        if not paiement or paiement.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )
        
        # TODO: Générer un PDF de reçu et le retourner
        # Pour l'instant, on retourne une erreur
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Génération de reçu PDF non encore implémentée"
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type de document non supporté: {document_type}"
        )

