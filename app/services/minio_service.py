from datetime import timedelta
from typing import Optional
from minio import Minio
from minio.error import S3Error
from app.core.minio_client import minio_client, ensure_bucket_exists
from app.core.config import settings
import uuid
import logging

logger = logging.getLogger(__name__)


class MinioService:
    """Service pour gérer le stockage et les URLs signées sur Minio"""
    
    BUCKET_ATTESTATIONS = "attestations"
    BUCKET_PROJECT_DOCUMENTS = "project-documents"
    BUCKET_LOGOS = "logos"

    @staticmethod
    def ensure_logos_bucket():
        """S'assure que le bucket logos (logos assureurs, etc.) existe."""
        ensure_bucket_exists(MinioService.BUCKET_LOGOS)

    @staticmethod
    def upload_assureur_logo(assureur_id: int, file_bytes: bytes, content_type: str, extension: str = "png") -> str:
        """
        Upload le logo d'un assureur dans MinIO et retourne la clé de l'objet (à stocker en logo_url).
        La clé est de la forme: assureurs/{id}/logo.{ext}
        """
        MinioService.ensure_logos_bucket()
        object_name = f"assureurs/{assureur_id}/logo.{extension.lstrip('.')}"
        try:
            from io import BytesIO
            file_io = BytesIO(file_bytes)
            minio_client.put_object(
                MinioService.BUCKET_LOGOS,
                object_name,
                file_io,
                length=len(file_bytes),
                content_type=content_type,
            )
            return object_name
        except S3Error as e:
            raise Exception(f"Erreur lors de l'upload du logo assureur sur MinIO: {str(e)}")
    
    @staticmethod
    def ensure_attestations_bucket():
        """S'assure que le bucket attestations existe"""
        ensure_bucket_exists(MinioService.BUCKET_ATTESTATIONS)

    @staticmethod
    def ensure_project_documents_bucket():
        """S'assure que le bucket dédié aux projets existe."""
        ensure_bucket_exists(MinioService.BUCKET_PROJECT_DOCUMENTS)
    
    @staticmethod
    def upload_pdf(
        pdf_buffer: bytes,
        souscription_id: int,
        type_attestation: str,
        numero_attestation: str
    ) -> str:
        """
        Upload un PDF sur Minio et retourne le chemin du fichier
        
        Args:
            pdf_buffer: Contenu du PDF en bytes
            souscription_id: ID de la souscription
            type_attestation: 'provisoire' ou 'definitive'
            numero_attestation: Numéro de l'attestation
            
        Returns:
            Chemin du fichier dans Minio
        """
        MinioService.ensure_attestations_bucket()
        
        # Générer un nom de fichier unique
        file_name = f"{souscription_id}/{type_attestation}/{numero_attestation}_{uuid.uuid4().hex[:8]}.pdf"
        
        # Upload le fichier
        try:
            from io import BytesIO
            pdf_io = BytesIO(pdf_buffer)
            minio_client.put_object(
                MinioService.BUCKET_ATTESTATIONS,
                file_name,
                pdf_io,
                length=len(pdf_buffer),
                content_type="application/pdf"
            )
            return file_name
        except S3Error as e:
            raise Exception(f"Erreur lors de l'upload du PDF sur Minio: {str(e)}")
    
    @staticmethod
    def upload_card_image(
        image_buffer: bytes,
        souscription_id: int,
        numero_attestation: str,
        extension: str = "png"
    ) -> str:
        """Upload une carte numérique (image) et retourne son chemin."""
        MinioService.ensure_attestations_bucket()
        file_name = f"{souscription_id}/cards/{numero_attestation}_{uuid.uuid4().hex[:8]}.{extension}"
        try:
            from io import BytesIO
            image_io = BytesIO(image_buffer)
            minio_client.put_object(
                MinioService.BUCKET_ATTESTATIONS,
                file_name,
                image_io,
                length=len(image_buffer),
                content_type=f"image/{extension}"
            )
            return file_name
        except S3Error as e:
            raise Exception(f"Erreur lors de l'upload de la carte numérique sur Minio: {str(e)}")
    
    @staticmethod
    def file_exists(bucket_name: str, object_name: str) -> bool:
        """
        Vérifie si un fichier existe dans Minio
        
        Args:
            bucket_name: Nom du bucket
            object_name: Nom de l'objet (chemin du fichier)
            
        Returns:
            True si le fichier existe, False sinon
        """
        try:
            minio_client.stat_object(bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            # Pour les autres erreurs, on log et on retourne False
            logger.warning(f"Erreur lors de la vérification de l'existence du fichier {object_name} dans {bucket_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la vérification de l'existence du fichier: {e}")
            return False
    
    @staticmethod
    def extract_error_details(error: Exception) -> dict:
        """
        Extrait toutes les informations disponibles d'une erreur MinIO/S3
        
        Args:
            error: L'exception à analyser
            
        Returns:
            Dictionnaire avec les détails de l'erreur
        """
        details = {
            'code': getattr(error, 'code', None),
            'message': getattr(error, 'message', None),
            'resource': getattr(error, 'resource', None),
            'request_id': getattr(error, 'request_id', None),
            'host_id': getattr(error, 'host_id', None),
            'bucket_name': getattr(error, 'bucket_name', None),
            'key': getattr(error, 'key', None),
            'error_string': str(error),
            'error_type': type(error).__name__
        }
        
        # Essayer d'extraire des informations depuis la représentation string
        error_str = str(error)
        if '<Resource>' in error_str:
            import re
            resource_match = re.search(r'<Resource>(.*?)</Resource>', error_str, re.DOTALL)
            if resource_match:
                details['resource'] = resource_match.group(1).strip()
        
        if '<RequestId>' in error_str:
            import re
            request_id_match = re.search(r'<RequestId>(.*?)</RequestId>', error_str, re.DOTALL)
            if request_id_match:
                details['request_id'] = request_id_match.group(1).strip()
        
        if '<HostId>' in error_str:
            import re
            host_id_match = re.search(r'<HostId>(.*?)</HostId>', error_str, re.DOTALL)
            if host_id_match:
                details['host_id'] = host_id_match.group(1).strip()
        
        if '<Code>' in error_str:
            import re
            code_match = re.search(r'<Code>(.*?)</Code>', error_str, re.DOTALL)
            if code_match:
                details['code'] = code_match.group(1).strip()
        
        if '<Message>' in error_str:
            import re
            message_match = re.search(r'<Message>(.*?)</Message>', error_str, re.DOTALL)
            if message_match:
                details['message'] = message_match.group(1).strip()
        
        return details
    
    @staticmethod
    def is_expired_url_error(error: Exception) -> bool:
        """
        Vérifie si une erreur est liée à une URL expirée
        
        Args:
            error: L'exception à vérifier
            
        Returns:
            True si l'erreur indique une URL expirée
        """
        error_str = str(error).lower()
        error_msg = getattr(error, 'message', '')
        error_code = getattr(error, 'code', '')
        
        # Extraire les détails pour une analyse plus complète
        details = MinioService.extract_error_details(error)
        if details.get('message'):
            error_msg = details['message']
        if details.get('code'):
            error_code = details['code']
        
        # Vérifier les différents formats d'erreur d'expiration
        expired_indicators = [
            'request has expired',
            'expired',
            'accessdenied',
            'signature does not match'
        ]
        
        return (
            error_code == 'AccessDenied' and 'expired' in error_msg.lower()
        ) or any(indicator in error_str for indicator in expired_indicators)
    
    @staticmethod
    def generate_signed_url(
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(hours=24),  # 24h par défaut (au lieu de 1h)
        retry_on_expired: bool = True
    ) -> str:
        """
        Génère une URL signée pour accéder à un objet Minio
        
        Args:
            bucket_name: Nom du bucket
            object_name: Nom de l'objet (chemin du fichier)
            expires: Durée de validité de l'URL (défaut: 24 heures, max 7 jours pour AWS/MinIO)
            retry_on_expired: Si True, régénère l'URL en cas d'erreur d'expiration (défaut: True)
            
        Returns:
            URL signée
            
        Raises:
            Exception: Si le fichier n'existe pas ou en cas d'erreur MinIO
        """
        try:
            # Vérifier que le fichier existe avant de générer l'URL
            if not MinioService.file_exists(bucket_name, object_name):
                error_msg = f"Le fichier {object_name} n'existe pas dans le bucket {bucket_name}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            url = minio_client.presigned_get_object(
                bucket_name,
                object_name,
                expires=expires
            )
            
            # Log pour diagnostiquer les problèmes d'heure
            from datetime import datetime
            logger.debug(
                f"URL signée générée pour {bucket_name}/{object_name} "
                f"à {datetime.utcnow().isoformat()} avec expiration de {expires}"
            )
            
            return url
        except S3Error as e:
            # Extraire tous les détails de l'erreur
            error_details = MinioService.extract_error_details(e)
            error_code = error_details.get('code') or 'Unknown'
            error_msg = error_details.get('message') or str(e)
            resource = error_details.get('resource')
            request_id = error_details.get('request_id')
            host_id = error_details.get('host_id')
            
            # Construire un message d'erreur détaillé
            error_info = f"Code: {error_code}, Message: {error_msg}"
            if resource:
                error_info += f", Resource: {resource}"
            if request_id:
                error_info += f", RequestId: {request_id}"
            if host_id:
                error_info += f", HostId: {host_id[:20]}..."  # Tronquer pour les logs
            
            # Si c'est une erreur d'expiration et qu'on peut réessayer, régénérer l'URL
            if retry_on_expired and MinioService.is_expired_url_error(e):
                logger.warning(
                    f"URL expirée détectée pour {bucket_name}/{object_name}. "
                    f"Régénération de l'URL... ({error_info})"
                )
                # Réessayer avec une nouvelle génération (sans vérification d'existence pour éviter la boucle)
                try:
                    url = minio_client.presigned_get_object(
                        bucket_name,
                        object_name,
                        expires=expires
                    )
                    logger.info(f"URL régénérée avec succès pour {bucket_name}/{object_name}")
                    return url
                except Exception as retry_error:
                    retry_details = MinioService.extract_error_details(retry_error)
                    logger.error(
                        f"Échec de la régénération de l'URL: {retry_error}. "
                        f"Détails: {retry_details}"
                    )
                    raise Exception(
                        f"Impossible de régénérer l'URL signée pour {bucket_name}/{object_name}. "
                        f"Vérifiez la synchronisation de l'heure du serveur. Erreur originale: {error_info}"
                    )
            
            detailed_error = (
                f"Erreur MinIO lors de la génération de l'URL signée pour {bucket_name}/{object_name}. "
                f"{error_info}"
            )
            logger.error(detailed_error, exc_info=True)
            raise Exception(detailed_error)
        except Exception as e:
            # Si c'est déjà notre exception personnalisée, la relancer
            if "n'existe pas" in str(e) or "Impossible de régénérer" in str(e):
                raise
            # Sinon, wrapper dans une exception plus descriptive
            detailed_error = f"Erreur lors de la génération de l'URL signée pour {bucket_name}/{object_name}: {str(e)}"
            logger.error(detailed_error)
            raise Exception(detailed_error)
    
    @staticmethod
    def get_file(bucket_name: str, object_name: str) -> Optional[bytes]:
        """
        Récupère un fichier depuis Minio
        
        Args:
            bucket_name: Nom du bucket
            object_name: Nom de l'objet (chemin du fichier)
            
        Returns:
            Contenu du fichier en bytes, ou None si erreur
        """
        try:
            from io import BytesIO
            response = minio_client.get_object(bucket_name, object_name)
            file_bytes = response.read()
            response.close()
            response.release_conn()
            return file_bytes
        except S3Error as e:
            logger = __import__('logging').getLogger(__name__)
            logger.warning(f"Erreur lors de la récupération du fichier {object_name} depuis Minio: {e}")
            return None
        except Exception as e:
            logger = __import__('logging').getLogger(__name__)
            logger.error(f"Erreur inattendue lors de la récupération du fichier: {e}")
            return None
    
    @staticmethod
    def get_pdf_url(
        chemin_fichier: str,
        bucket_name: Optional[str] = None,
        expires: timedelta = timedelta(hours=24)  # 24h par défaut (au lieu de 1h)
    ) -> str:
        """
        Récupère une URL signée pour un PDF d'attestation
        
        Args:
            chemin_fichier: Chemin du fichier dans Minio
            bucket_name: Nom du bucket (défaut: BUCKET_ATTESTATIONS)
            expires: Durée de validité de l'URL
            
        Returns:
            URL signée
            
        Raises:
            Exception: Si le fichier n'existe pas ou en cas d'erreur MinIO
        """
        if bucket_name is None:
            bucket_name = MinioService.BUCKET_ATTESTATIONS
        
        try:
            return MinioService.generate_signed_url(bucket_name, chemin_fichier, expires)
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'URL pour le PDF {chemin_fichier} dans {bucket_name}: {e}")
            raise
    
    @staticmethod
    def delete_pdf(bucket_name: str, object_name: str) -> bool:
        """
        Supprime un PDF de Minio
        
        Args:
            bucket_name: Nom du bucket
            object_name: Nom de l'objet
            
        Returns:
            True si supprimé avec succès
        """
        try:
            minio_client.remove_object(bucket_name, object_name)
            return True
        except S3Error as e:
            raise Exception(f"Erreur lors de la suppression du PDF: {str(e)}")
    
    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_data: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload un fichier générique sur Minio
        
        Args:
            bucket_name: Nom du bucket
            object_name: Nom de l'objet (chemin du fichier)
            file_data: Contenu du fichier en bytes
            content_type: Type MIME du fichier
            
        Returns:
            Chemin du fichier dans Minio
        """
        ensure_bucket_exists(bucket_name)
        
        try:
            from io import BytesIO
            file_io = BytesIO(file_data)
            minio_client.put_object(
                bucket_name,
                object_name,
                file_io,
                length=len(file_data),
                content_type=content_type
            )
            return object_name
        except S3Error as e:
            raise Exception(f"Erreur lors de l'upload du fichier sur Minio: {str(e)}")

