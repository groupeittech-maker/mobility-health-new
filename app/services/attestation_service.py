from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from base64 import b64encode, b64decode
import logging
import uuid
from sqlalchemy.orm import Session
from app.models.attestation import Attestation
from app.models.souscription import Souscription
from app.models.paiement import Paiement
from app.models.user import User
from app.models.validation_attestation import ValidationAttestation
from app.models.questionnaire import Questionnaire
from app.services.pdf_service import PDFService
from app.services.minio_service import MinioService
from app.services.qrcode_service import QRCodeService
from app.services.card_service import CardService
from app.core.config import settings


logger = logging.getLogger(__name__)

INLINE_BUCKET_NAME = "inline"
INLINE_OBJECT_KEY = "INLINE_PDF"


class AttestationService:
    """Service pour gérer les attestations"""
    
    @staticmethod
    def generate_numero_attestation(souscription: Souscription, type_attestation: str) -> str:
        """Génère un numéro d'attestation unique"""
        prefix = "ATT-PROV" if type_attestation == "provisoire" else "ATT-DEF"
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"{prefix}-{souscription.numero_souscription}-{date_str}-{unique_id}"
    
    @staticmethod
    def build_verification_url(numero_attestation: str) -> str:
        base = settings.ATTESTATION_VERIFICATION_BASE_URL.rstrip('/')
        return f"{base}/attestations/verify/{numero_attestation}"
    
    @staticmethod
    def create_attestation_provisoire(
        db: Session,
        souscription: Souscription,
        paiement: Paiement,
        user: Optional[User] = None
    ) -> Attestation:
        """
        Crée une attestation provisoire après paiement.
        
        IMPORTANT: 
        - La souscription est toujours liée à l'abonné (souscription.user_id)
        - Si c'est une souscription pour un tiers, les informations du tiers sont extraites
          depuis le questionnaire administratif et utilisées pour les documents (attestations, cartes)
        - L'objet user passé en paramètre est l'abonné (souscripteur), utilisé comme fallback
          si les informations du voyageur ne sont pas disponibles dans le questionnaire
        """
        from app.models.user import User as UserModel

        numero_attestation = AttestationService.generate_numero_attestation(souscription, "provisoire")
        verification_url = AttestationService.build_verification_url(numero_attestation)
        qr_buffer = QRCodeService.generate_qr_image(verification_url)

        # Extraire les informations du voyageur depuis le questionnaire administratif
        # Si c'est une souscription pour un tiers, cela retournera les informations du tiers
        # Sinon, cela retournera les informations de l'abonné depuis le questionnaire
        traveler_info = AttestationService._extract_traveler_info(db, souscription.id)
        
        # L'objet user est l'abonné (souscripteur) - utilisé comme fallback si traveler_info est vide
        # La souscription reste toujours liée à l'abonné (souscription.user_id)
        user_obj = user or db.query(UserModel).filter(UserModel.id == paiement.user_id).first()
        
        logger.info(
            f"📄 Création attestation provisoire - Souscription ID: {souscription.id}, "
            f"Abonné (user_id): {souscription.user_id}"
        )
        if traveler_info:
            logger.info(
                f"📄 Informations voyageur extraites - fullName: '{traveler_info.get('fullName', 'VIDE')}', "
                f"birthDate: '{traveler_info.get('birthDate', 'VIDE')}', "
                f"passportNumber: '{traveler_info.get('passportNumber', 'VIDE')}'"
            )
        else:
            logger.warning(
                f"⚠️ traveler_info est vide ou None pour souscription {souscription.id}"
            )

        pdf_buffer = PDFService.generate_attestation_provisoire(
            souscription,
            paiement,
            user_obj,  # Abonné (souscripteur) - utilisé comme fallback
            numero_attestation,
            qr_image_data=qr_buffer,
            verification_url=verification_url,
            traveler_info=traveler_info  # Informations du voyageur (tiers si souscription pour un tiers, sinon abonné)
        )
        pdf_bytes = pdf_buffer.read()
        
        # Upload sur Minio (fallback inline en cas d'échec)
        chemin_fichier = None
        url_signee = None
        bucket = MinioService.BUCKET_ATTESTATIONS
        date_expiration_url = None
        try:
            chemin_fichier = MinioService.upload_pdf(
                pdf_bytes,
                souscription.id,
                "provisoire",
                numero_attestation
            )
            # Générer une URL initiale (sera régénérée à chaque demande)
            url_signee = MinioService.get_pdf_url(chemin_fichier, expires=timedelta(hours=24))
            date_expiration_url = datetime.utcnow() + timedelta(hours=24)
        except Exception as storage_error:
            inline_payload = b64encode(pdf_bytes).decode("ascii")
            url_signee = f"data:application/pdf;base64,{inline_payload}"
            chemin_fichier = INLINE_OBJECT_KEY
            bucket = INLINE_BUCKET_NAME
            date_expiration_url = None
            logger.warning(
                "Minio indisponible pour l'attestation provisoire %s. Utilisation d'un stockage inline. Détail: %s",
                numero_attestation,
                storage_error,
            )
        
        # Créer l'attestation en base
        attestation = Attestation(
            souscription_id=souscription.id,
            paiement_id=paiement.id,
            type_attestation="provisoire",
            numero_attestation=numero_attestation,
            chemin_fichier_minio=chemin_fichier,
            bucket_minio=bucket,
            url_signee=url_signee,
            date_expiration_url=date_expiration_url,
            est_valide=True
        )
        
        db.add(attestation)
        db.commit()
        db.refresh(attestation)
        
        return attestation
    
    @staticmethod
    def create_attestation_definitive(
        db: Session,
        souscription: Souscription,
        paiement: Paiement,
        user: Optional[User] = None
    ) -> Attestation:
        """
        Crée une attestation définitive après toutes les validations.
        
        IMPORTANT: 
        - La souscription est toujours liée à l'abonné (souscription.user_id)
        - Si c'est une souscription pour un tiers, les informations du tiers sont extraites
          depuis le questionnaire administratif et utilisées pour les documents (attestations, cartes)
        - L'objet user passé en paramètre est l'abonné (souscripteur), utilisé comme fallback
          si les informations du voyageur ne sont pas disponibles dans le questionnaire
        """
        numero_attestation = AttestationService.generate_numero_attestation(souscription, "definitive")
        verification_url = AttestationService.build_verification_url(numero_attestation)
        qr_buffer = QRCodeService.generate_qr_image(verification_url)
        qr_bytes = qr_buffer.getvalue()

        # Extraire les informations du voyageur depuis le questionnaire administratif
        # Si c'est une souscription pour un tiers, cela retournera les informations du tiers
        # Sinon, cela retournera les informations de l'abonné depuis le questionnaire
        traveler_info = AttestationService._extract_traveler_info(db, souscription.id)
        
        # L'objet user est l'abonné (souscripteur) - utilisé comme fallback si traveler_info est vide
        # La souscription reste toujours liée à l'abonné (souscription.user_id)
        from app.models.user import User as UserModel
        user_obj = user or db.query(UserModel).filter(UserModel.id == souscription.user_id).first()
        
        logger.info(
            f"Création attestation définitive - Souscription ID: {souscription.id}, "
            f"Abonné (user_id): {souscription.user_id}, "
            f"Voyageur: {traveler_info.get('fullName', 'N/A') if traveler_info else 'N/A'}"
        )

        # Extraire les enfants mineurs à charge depuis les notes (souscription ou projet)
        minors_info = AttestationService._extract_minors_from_notes(souscription.notes or "")
        if not minors_info and souscription.projet_voyage_id:
            from app.models.projet_voyage import ProjetVoyage
            projet = db.query(ProjetVoyage).filter(
                ProjetVoyage.id == souscription.projet_voyage_id
            ).first()
            if projet and projet.notes:
                minors_info = AttestationService._extract_minors_from_notes(projet.notes)
        if minors_info:
            logger.info(
                "Attestation définitive: %d enfant(s) mineur(s) à charge déclaré(s)",
                len(minors_info),
            )

        pdf_buffer = PDFService.generate_attestation_definitive(
            souscription,
            paiement,
            user_obj,  # Abonné (souscripteur) - utilisé comme fallback
            numero_attestation,
            qr_image_data=qr_buffer,
            verification_url=verification_url,
            traveler_info=traveler_info,  # Informations du voyageur (tiers si souscription pour un tiers, sinon abonné)
            minors_info=minors_info,  # Enfants mineurs à charge (affichés dans l'attestation définitive)
        )
        pdf_bytes = pdf_buffer.read()
        
        # Upload sur Minio (fallback inline)
        chemin_fichier = None
        url_signee = None
        bucket = MinioService.BUCKET_ATTESTATIONS
        date_expiration_url = None
        try:
            chemin_fichier = MinioService.upload_pdf(
                pdf_bytes,
                souscription.id,
                "definitive",
                numero_attestation
            )
            url_signee = MinioService.get_pdf_url(chemin_fichier, expires=timedelta(hours=24))
            date_expiration_url = datetime.utcnow() + timedelta(hours=24)
        except Exception as storage_error:
            inline_payload = b64encode(pdf_bytes).decode("ascii")
            url_signee = f"data:application/pdf;base64,{inline_payload}"
            chemin_fichier = INLINE_OBJECT_KEY
            bucket = INLINE_BUCKET_NAME
            date_expiration_url = None
            logger.warning(
                "Minio indisponible pour l'attestation définitive %s. Utilisation d'un stockage inline. Détail: %s",
                numero_attestation,
                storage_error,
            )

        # Génération de la carte numérique (PNG)
        card_path = None
        card_bucket = None
        card_url = None
        card_expires = None
        card_bytes = None
        try:
            logger.info("Début de la génération de la carte numérique pour %s (souscription ID: %s)", 
                       numero_attestation, souscription.id)
            identity_photo = AttestationService._extract_identity_photo_bytes(db, souscription.id)
            logger.info("Photo d'identité extraite: %s (taille: %d bytes)", 
                       "Oui" if identity_photo else "Non", 
                       len(identity_photo) if identity_photo else 0)
            logger.info("QR bytes disponibles: %s", "Oui" if qr_bytes else "Non")
            
            # Générer la carte même si la photo n'est pas disponible (elle utilisera un placeholder)
            card_buffer = CardService.generate_insurance_card(
                user_obj,
                souscription,
                numero_attestation,
                verification_url,
                photo_bytes=identity_photo,
                qr_bytes=qr_bytes,
                traveler_info=traveler_info
            )
            card_bytes = card_buffer.getvalue()
            logger.info("Carte numérique générée avec succès, taille: %d bytes", len(card_bytes))
            
            # Upload sur Minio
            try:
                card_path = MinioService.upload_card_image(
                    card_bytes,
                    souscription.id,
                    numero_attestation
                )
                card_bucket = MinioService.BUCKET_ATTESTATIONS
                card_url = MinioService.generate_signed_url(
                    card_bucket,
                    card_path,
                    expires=timedelta(hours=24)
                )
                card_expires = datetime.utcnow() + timedelta(hours=24)
                logger.info(
                    "Carte numérique générée et uploadée avec succès pour %s",
                    numero_attestation
                )
            except Exception as upload_error:
                # Fallback: stockage inline si Minio échoue
                logger.warning(
                    "Échec de l'upload de la carte numérique sur Minio pour %s: %s. Utilisation du stockage inline.",
                    numero_attestation,
                    upload_error,
                )
                inline_payload = b64encode(card_bytes).decode("ascii")
                card_url = f"data:image/png;base64,{inline_payload}"
                card_path = INLINE_OBJECT_KEY
                card_bucket = INLINE_BUCKET_NAME
                card_expires = None
        except Exception as card_error:
            # Log l'erreur complète avec traceback pour le débogage
            import traceback
            logger.error(
                "Erreur lors de la génération de la carte numérique pour %s: %s\nTraceback: %s",
                numero_attestation,
                str(card_error),
                traceback.format_exc(),
            )
            # Si card_bytes existe (génération réussie mais erreur après), utiliser le fallback inline
            if card_bytes:
                try:
                    inline_payload = b64encode(card_bytes).decode("ascii")
                    card_url = f"data:image/png;base64,{inline_payload}"
                    card_path = INLINE_OBJECT_KEY
                    card_bucket = INLINE_BUCKET_NAME
                    card_expires = None
                    logger.warning(
                        "Carte numérique générée mais erreur lors de l'upload. Utilisation du stockage inline pour %s",
                        numero_attestation
                    )
                except Exception as inline_error:
                    logger.error(
                        "Impossible de sauvegarder la carte numérique en mode inline pour %s: %s",
                        numero_attestation,
                        inline_error
                    )
            else:
                logger.error(
                    "Impossible de générer la carte numérique pour %s. Aucune carte ne sera créée. "
                    "L'attestation sera créée sans carte, mais elle pourra être générée ultérieurement lors de la validation de production.",
                    numero_attestation
                )
                # Ne pas bloquer la création de l'attestation même si la carte échoue
                # La carte sera générée lors de la validation de production
        
        # Créer l'attestation en base
        attestation = Attestation(
            souscription_id=souscription.id,
            paiement_id=paiement.id,
            type_attestation="definitive",
            numero_attestation=numero_attestation,
            chemin_fichier_minio=chemin_fichier,
            bucket_minio=bucket,
            url_signee=url_signee,
            date_expiration_url=date_expiration_url,
            carte_numerique_path=card_path,
            carte_numerique_bucket=card_bucket,
            carte_numerique_url=card_url,
            carte_numerique_expires_at=card_expires,
            est_valide=True
        )
        
        db.add(attestation)
        db.commit()
        db.refresh(attestation)
        
        # Vérifier que la carte a bien été créée
        if not card_url:
            logger.warning(
                "ATTENTION: L'attestation définitive %s (ID: %s) a été créée SANS carte numérique. "
                "Vérifiez les logs précédents pour identifier la cause. "
                "La carte sera générée automatiquement lors de la validation de production.",
                numero_attestation,
                attestation.id
            )
        else:
            logger.info(
                "Attestation définitive créée avec succès: %s (ID: %s). "
                "Carte numérique: %s (path: %s, bucket: %s)",
                numero_attestation,
                attestation.id,
                "inline" if card_bucket == INLINE_BUCKET_NAME else "Minio",
                card_path or "N/A",
                card_bucket or "N/A"
            )
        
        # Notification retirée : l'utilisateur n'est plus notifié lors de la création de l'attestation définitive
        
        return attestation
    
    @staticmethod
    def refresh_signed_url(
        db: Session,
        attestation: Attestation,
        expires: timedelta = timedelta(hours=1),
        refresh_card: bool = False
    ) -> str:
        """Rafraîchit l'URL signée d'une attestation"""
        now = datetime.utcnow()
        if attestation.bucket_minio == INLINE_BUCKET_NAME or attestation.chemin_fichier_minio == INLINE_OBJECT_KEY:
            # Rien à rafraîchir pour un stockage inline (data URI)
            url_signee = attestation.url_signee
        else:
            url_signee = MinioService.get_pdf_url(
                attestation.chemin_fichier_minio,
                attestation.bucket_minio,
                expires
            )
            attestation.url_signee = url_signee
            attestation.date_expiration_url = now + expires

        if refresh_card and attestation.carte_numerique_path and attestation.carte_numerique_bucket:
            is_inline_card = attestation.carte_numerique_bucket == INLINE_BUCKET_NAME or \
                attestation.carte_numerique_path == INLINE_OBJECT_KEY
            if not is_inline_card:
                needs_refresh = (
                    not attestation.carte_numerique_url or
                    not attestation.carte_numerique_expires_at or
                    attestation.carte_numerique_expires_at <= now + timedelta(minutes=5)
                )
                if needs_refresh:
                    bucket = attestation.carte_numerique_bucket or MinioService.BUCKET_ATTESTATIONS
                    attestation.carte_numerique_url = MinioService.generate_signed_url(
                        bucket,
                        attestation.carte_numerique_path,
                        expires
                    )
                    attestation.carte_numerique_expires_at = now + expires

        db.commit()
        return url_signee
    
    @staticmethod
    def check_all_validations_complete(db: Session, attestation_provisoire: Attestation) -> bool:
        """Vérifie si la validation production est complète pour générer l'attestation définitive.
        La validation médicale est effectuée à l'inscription, elle n'est plus requise ici."""
        validations = db.query(ValidationAttestation).filter(
            ValidationAttestation.attestation_id == attestation_provisoire.id
        ).all()
        
        required_types = {"production"}
        validated_types = set()
        for validation in validations:
            if not validation.est_valide:
                continue
            normalized_type = "production" if validation.type_validation == "agpmh" else validation.type_validation
            validated_types.add(normalized_type)
        
        return required_types.issubset(validated_types)

    @staticmethod
    def _extract_traveler_info(db: Session, souscription_id: int) -> Dict[str, Any]:
        """
        Extrait les informations du voyageur depuis le questionnaire administratif.
        
        IMPORTANT: 
        - Si c'est une souscription pour un tiers, cette fonction retourne les informations
          du tiers (bénéficiaire) depuis les notes du projet ou de la souscription.
        - Sinon, elle retourne les informations de l'abonné depuis le questionnaire administratif.
        - La souscription elle-même reste toujours liée à l'abonné (souscription.user_id).
        - Ces informations sont utilisées uniquement pour les documents (attestations, cartes).
        
        Retourne un dictionnaire avec les informations du voyageur ou {} si non trouvé.
        """
        from app.models.souscription import Souscription as SouscriptionModel
        from app.models.projet_voyage import ProjetVoyage
        
        # Récupérer la souscription pour vérifier si c'est pour un tiers
        souscription = db.query(SouscriptionModel).filter(
            SouscriptionModel.id == souscription_id
        ).first()
        
        if not souscription:
            logger.warning("Souscription %s non trouvée", souscription_id)
            return {}
        
        # Vérifier si c'est une souscription pour un tiers en cherchant dans les notes
        is_tier_subscription = False
        tier_info = {}
        
        # Chercher dans les notes du voyage
        if souscription.projet_voyage_id:
            projet = db.query(ProjetVoyage).filter(
                ProjetVoyage.id == souscription.projet_voyage_id
            ).first()
            
            if projet and projet.notes:
                # Vérifier si c'est une souscription pour un tiers
                if "Pour un tiers" in projet.notes or "pour un tiers" in projet.notes.lower():
                    is_tier_subscription = True
                    # Extraire les informations du tiers depuis les notes
                    tier_info = AttestationService._extract_tier_info_from_notes(projet.notes)
        
        # Chercher aussi dans les notes de la souscription
        if not is_tier_subscription and souscription.notes:
            if "Pour un tiers" in souscription.notes or "pour un tiers" in souscription.notes.lower():
                is_tier_subscription = True
                tier_info = AttestationService._extract_tier_info_from_notes(souscription.notes)
        
        # IMPORTANT: Pour une souscription pour un tiers, les informations du tiers sont dans
        # le questionnaire administratif (rempli par l'utilisateur avec les infos du tiers).
        # Les notes peuvent contenir une indication "Pour un tiers" mais les vraies informations
        # (nom, date de naissance, passeport, etc.) sont dans le questionnaire.
        
        # Récupérer le questionnaire administratif (contient les infos du tiers si souscription pour un tiers)
        # IMPORTANT: Utiliser la session de base de données passée en paramètre
        from app.models.questionnaire import Questionnaire as QuestionnaireModel
        
        # Vérifier d'abord combien de questionnaires existent pour cette souscription
        all_questionnaires = (
            db.query(QuestionnaireModel)
            .filter(QuestionnaireModel.souscription_id == souscription_id)
            .all()
        )
        logger.info(
            "🔍 Questionnaires trouvés pour souscription %s: %d (tous types)",
            souscription_id,
            len(all_questionnaires)
        )
        
        questionnaire = (
            db.query(QuestionnaireModel)
            .filter(
                QuestionnaireModel.souscription_id == souscription_id,
                QuestionnaireModel.type_questionnaire == "administratif",
            )
            .order_by(QuestionnaireModel.version.desc())
            .first()
        )

        if not questionnaire:
            logger.error(
                "❌ ERREUR: Aucun questionnaire administratif trouvé pour la souscription %s",
                souscription_id
            )
            logger.error(
                "❌ Questionnaires disponibles: %s",
                [(q.id, q.type_questionnaire, q.version) for q in all_questionnaires]
            )
            # Si c'est pour un tiers mais pas de questionnaire, essayer les notes comme fallback
            if is_tier_subscription and tier_info:
                logger.info(
                    "Souscription %s est pour un tiers, utilisation des informations du tiers depuis les notes (fallback)",
                    souscription_id
                )
                return tier_info
            return {}
        
        if not questionnaire.reponses:
            logger.error(
                "❌ ERREUR: Questionnaire administratif trouvé (ID: %s) mais reponses est vide pour souscription %s",
                questionnaire.id,
                souscription_id
            )
            # Si c'est pour un tiers mais pas de questionnaire, essayer les notes comme fallback
            if is_tier_subscription and tier_info:
                logger.info(
                    "Souscription %s est pour un tiers, utilisation des informations du tiers depuis les notes (fallback)",
                    souscription_id
                )
                return tier_info
            return {}

        personal = questionnaire.reponses.get("personal") or {}
        
        # DEBUG: Logger le contenu complet du questionnaire pour diagnostic
        logger.info(
            "🔍 Extraction traveler_info - Souscription ID: %s, is_tier_subscription: %s",
            souscription_id,
            is_tier_subscription
        )
        logger.info(
            "🔍 Questionnaire reponses keys: %s",
            list(questionnaire.reponses.keys()) if questionnaire.reponses else "None"
        )
        logger.info(
            "🔍 Personal keys: %s",
            list(personal.keys()) if personal else "None"
        )
        
        # IMPORTANT: Gérer les différents formats de nom
        # - Format 1: fullName (nom complet en un seul champ) - utilisé à l'inscription
        # - Format 2: nom + prenom (champs séparés en français) - utilisé pour le tiers
        # - Format 3: firstName + lastName (champs séparés en anglais avec majuscules)
        # - Format 4: firstname + lastname (champs séparés en anglais avec minuscules)
        full_name = ""
        
        if personal.get("fullName"):
            # Format 1: nom complet en un seul champ
            full_name = personal.get("fullName", "").strip()
            logger.info("🔍 Format fullName trouvé: '%s'", full_name)
        elif personal.get("nom") or personal.get("prenom"):
            # Format 2: nom et prénom séparés (français)
            nom = personal.get("nom", "").strip()
            prenom = personal.get("prenom", "").strip()
            full_name = f"{prenom} {nom}".strip() if prenom or nom else ""
            logger.info("🔍 Format nom/prenom trouvé: nom='%s', prenom='%s' → fullName='%s'", nom, prenom, full_name)
        elif personal.get("firstName") or personal.get("lastName"):
            # Format 3: firstName et lastName séparés (anglais avec majuscules)
            first_name = personal.get("firstName", "").strip()
            last_name = personal.get("lastName", "").strip()
            full_name = f"{first_name} {last_name}".strip() if first_name or last_name else ""
            logger.info("🔍 Format firstName/lastName trouvé: firstName='%s', lastName='%s' → fullName='%s'", first_name, last_name, full_name)
        elif personal.get("firstname") or personal.get("lastname"):
            # Format 4: firstname et lastname séparés (anglais avec minuscules)
            first_name = personal.get("firstname", "").strip()
            last_name = personal.get("lastname", "").strip()
            full_name = f"{first_name} {last_name}".strip() if first_name or last_name else ""
            logger.info("🔍 Format firstname/lastname trouvé: firstname='%s', lastname='%s' → fullName='%s'", first_name, last_name, full_name)
        else:
            logger.warning("⚠️ Aucun format de nom trouvé dans personal. Keys disponibles: %s", list(personal.keys()) if personal else "None")
        
        # Extraire les informations du voyageur depuis le questionnaire
        # Si c'est une souscription pour un tiers, le questionnaire contient les infos du tiers
        # Sinon, il contient les infos de l'abonné
        traveler_info = {
            "fullName": full_name,
            "birthDate": personal.get("birthDate") or personal.get("date_naissance") or "",
            "birthPlace": personal.get("birthPlace") or personal.get("lieu_naissance") or personal.get("lieu_naissance_ville") or "",
            "gender": personal.get("gender") or personal.get("sexe") or "",
            "nationality": personal.get("nationality") or personal.get("nationalite") or "",
            "passportNumber": personal.get("passportNumber") or personal.get("numero_passeport") or personal.get("numero_piece_identite") or "",
            "passportExpiryDate": personal.get("passportExpiryDate") or personal.get("date_expiration_passeport") or personal.get("date_expiration") or "",
            "address": personal.get("address") or personal.get("adresse") or personal.get("adresse_residence") or "",
            "phone": personal.get("phone") or personal.get("telephone") or "",
            "email": personal.get("email") or "",
            "profession": personal.get("profession") or personal.get("occupation") or personal.get("metier") or "",
        }
        
        # Si c'est une souscription pour un tiers, vérifier si on a les informations
        if is_tier_subscription:
            # Si fullName est vide dans le questionnaire, utiliser les informations depuis les notes
            if not traveler_info.get("fullName") and tier_info:
                logger.warning(
                    "⚠️ fullName vide dans le questionnaire pour souscription %s, utilisation des informations depuis les notes",
                    souscription_id
                )
                # Remplacer les informations vides par celles des notes
                if tier_info.get("fullName"):
                    traveler_info["fullName"] = tier_info["fullName"]
                if tier_info.get("birthDate") and not traveler_info.get("birthDate"):
                    traveler_info["birthDate"] = tier_info["birthDate"]
                if tier_info.get("passportNumber") and not traveler_info.get("passportNumber"):
                    traveler_info["passportNumber"] = tier_info["passportNumber"]
                if tier_info.get("passportExpiryDate") and not traveler_info.get("passportExpiryDate"):
                    traveler_info["passportExpiryDate"] = tier_info["passportExpiryDate"]
                if tier_info.get("phone") and not traveler_info.get("phone"):
                    traveler_info["phone"] = tier_info["phone"]
            
            logger.info(
                "✅ Souscription %s est pour un tiers, utilisation des informations du tiers",
                souscription_id
            )
            logger.info(
                "✅ Informations du tiers extraites - fullName: '%s', birthDate: '%s', passportNumber: '%s'",
                traveler_info.get("fullName", "VIDE"),
                traveler_info.get("birthDate", "VIDE"),
                traveler_info.get("passportNumber", "VIDE")
            )
            
            # Si fullName est toujours vide après avoir essayé les notes, c'est un problème !
            if not traveler_info.get("fullName"):
                logger.error(
                    "❌ ERREUR: Souscription pour un tiers mais fullName est vide même après extraction depuis les notes !"
                )
                logger.error(
                    "❌ Contenu complet de personal: %s",
                    personal
                )
                logger.error(
                    "❌ Contenu de tier_info depuis les notes: %s",
                    tier_info
                )
        else:
            logger.debug(
                "Souscription %s - utilisation des informations de l'abonné depuis le questionnaire: %s",
                souscription_id,
                traveler_info.get("fullName", "N/A")
            )
        
        return traveler_info
    
    @staticmethod
    def _extract_tier_info_from_notes(notes: str) -> Dict[str, Any]:
        """
        Extrait les informations du tiers depuis les notes du voyage ou de la souscription.
        Format attendu dans les notes (exemple):
        === INFORMATIONS DU TIERS (BÉNÉFICIAIRE) ===
        Nom du tiers: ...
        Prénom du tiers: ...
        Date de naissance du tiers: ...
        Numéro de passeport du tiers: ...
        Date d'expiration du passeport du tiers: ...
        Téléphone d'urgence du tiers: ...
        === FIN INFORMATIONS DU TIERS ===
        """
        import re
        from datetime import datetime
        
        tier_info = {}
        
        if not notes:
            logger.warning("⚠️ _extract_tier_info_from_notes: notes est vide")
            return tier_info
        
        logger.info("🔍 Extraction des informations du tiers depuis les notes (longueur: %d caractères)", len(notes))
        
        # Extraire le nom (chercher différentes variantes)
        # Format JSON possible: {"lastname": "...", "firstname": "..."}
        # Format texte: "Nom du tiers: ..." ou "lastname: ..."
        import json
        try:
            # Essayer de parser comme JSON d'abord
            json_match = re.search(r'\{[^}]*"lastname"[^}]*\}', notes, re.IGNORECASE | re.DOTALL)
            if json_match:
                json_data = json.loads(json_match.group(0))
                tier_info["lastName"] = json_data.get("lastname", "")
                tier_info["firstName"] = json_data.get("firstname", "")
        except:
            pass
        
        # Si pas trouvé en JSON, chercher en format texte
        if not tier_info.get("lastName"):
            name_patterns = [
                r'Nom du tiers[:\s]+([^\n]+)',
                r'Nom[:\s]+([^\n]+)',
                r'lastname[:\s]+([^\n]+)',
                r'"lastname"[:\s]*"([^"]+)"',
            ]
            for pattern in name_patterns:
                match = re.search(pattern, notes, re.IGNORECASE)
                if match:
                    tier_info["lastName"] = match.group(1).strip()
                    break
        
        # Extraire le prénom
        if not tier_info.get("firstName"):
            firstname_patterns = [
                r'Prénom du tiers[:\s]+([^\n]+)',
                r'Prénom[:\s]+([^\n]+)',
                r'firstname[:\s]+([^\n]+)',
                r'"firstname"[:\s]*"([^"]+)"',
            ]
            for pattern in firstname_patterns:
                match = re.search(pattern, notes, re.IGNORECASE)
                if match:
                    tier_info["firstName"] = match.group(1).strip()
                    break
        
        # Construire fullName si on a nom et prénom
        if tier_info.get("lastName") and tier_info.get("firstName"):
            tier_info["fullName"] = f"{tier_info['firstName']} {tier_info['lastName']}"
        elif tier_info.get("lastName"):
            tier_info["fullName"] = tier_info["lastName"]
        elif tier_info.get("firstName"):
            tier_info["fullName"] = tier_info["firstName"]
        
        # Extraire la date de naissance
        # Format JSON possible: {"birthdate": "..."}
        # Format texte: "Date de naissance du tiers: ..." ou "birthdate: ..."
        if not tier_info.get("birthDate"):
            try:
                json_match = re.search(r'\{[^}]*"birthdate"[^}]*\}', notes, re.IGNORECASE | re.DOTALL)
                if json_match:
                    json_data = json.loads(json_match.group(0))
                    birthdate_str = json_data.get("birthdate", "")
                    if birthdate_str:
                        tier_info["birthDate"] = birthdate_str
            except:
                pass
        
        if not tier_info.get("birthDate"):
            birthdate_patterns = [
                r'Date de naissance du tiers[:\s]+([^\n]+)',
                r'Date de naissance[:\s]+([^\n]+)',
                r'birthdate[:\s]+([^\n]+)',
                r'"birthdate"[:\s]*"([^"]+)"',
            ]
            for pattern in birthdate_patterns:
                match = re.search(pattern, notes, re.IGNORECASE)
                if match:
                    birthdate_str = match.group(1).strip()
                    # Essayer de parser la date
                    try:
                        # Formats possibles: YYYY-MM-DD, DD/MM/YYYY, etc.
                        if '/' in birthdate_str:
                            # Format DD/MM/YYYY
                            parts = birthdate_str.split('/')
                            if len(parts) == 3:
                                birthdate_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
                        tier_info["birthDate"] = birthdate_str
                    except:
                        tier_info["birthDate"] = birthdate_str
                    break
        
        # Extraire le numéro de passeport
        # Format JSON possible: {"passportNumber": "..."}
        if not tier_info.get("passportNumber"):
            try:
                json_match = re.search(r'\{[^}]*"passportNumber"[^}]*\}', notes, re.IGNORECASE | re.DOTALL)
                if json_match:
                    json_data = json.loads(json_match.group(0))
                    tier_info["passportNumber"] = json_data.get("passportNumber", "")
            except:
                pass
        
        if not tier_info.get("passportNumber"):
            passport_patterns = [
                r'Numéro de passeport du tiers[:\s]+([^\n]+)',
                r'Numéro de passeport[:\s]+([^\n]+)',
                r'passportNumber[:\s]+([^\n]+)',
                r'"passportNumber"[:\s]*"([^"]+)"',
            ]
            for pattern in passport_patterns:
                match = re.search(pattern, notes, re.IGNORECASE)
                if match:
                    tier_info["passportNumber"] = match.group(1).strip()
                    break
        
        # Extraire la date d'expiration du passeport
        if not tier_info.get("passportExpiryDate"):
            try:
                json_match = re.search(r'\{[^}]*"passportExpiryDate"[^}]*\}', notes, re.IGNORECASE | re.DOTALL)
                if json_match:
                    json_data = json.loads(json_match.group(0))
                    expiry_str = json_data.get("passportExpiryDate", "")
                    if expiry_str:
                        tier_info["passportExpiryDate"] = expiry_str
            except:
                pass
        
        if not tier_info.get("passportExpiryDate"):
            passport_expiry_patterns = [
                r'Date d\'expiration du passeport du tiers[:\s]+([^\n]+)',
                r'Date d\'expiration du passeport[:\s]+([^\n]+)',
                r'passportExpiryDate[:\s]+([^\n]+)',
                r'"passportExpiryDate"[:\s]*"([^"]+)"',
            ]
            for pattern in passport_expiry_patterns:
                match = re.search(pattern, notes, re.IGNORECASE)
                if match:
                    expiry_str = match.group(1).strip()
                    try:
                        if '/' in expiry_str:
                            parts = expiry_str.split('/')
                            if len(parts) == 3:
                                expiry_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
                        tier_info["passportExpiryDate"] = expiry_str
                    except:
                        tier_info["passportExpiryDate"] = expiry_str
                    break
        
        # Extraire le téléphone d'urgence
        if not tier_info.get("phone"):
            try:
                json_match = re.search(r'\{[^}]*"emergencyPhone"[^}]*\}', notes, re.IGNORECASE | re.DOTALL)
                if json_match:
                    json_data = json.loads(json_match.group(0))
                    tier_info["phone"] = json_data.get("emergencyPhone", "")
            except:
                pass
        
        if not tier_info.get("phone"):
            emergency_phone_patterns = [
                r'Téléphone d\'urgence du tiers[:\s]+([^\n]+)',
                r'Téléphone d\'urgence[:\s]+([^\n]+)',
                r'emergencyPhone[:\s]+([^\n]+)',
                r'"emergencyPhone"[:\s]*"([^"]+)"',
            ]
            for pattern in emergency_phone_patterns:
                match = re.search(pattern, notes, re.IGNORECASE)
                if match:
                    tier_info["phone"] = match.group(1).strip()
                    break
        
        return tier_info

    @staticmethod
    def _extract_minors_from_notes(notes: str) -> List[Dict[str, str]]:
        """
        Extrait la liste des enfants mineurs à charge depuis les notes du projet ou de la souscription.
        Format attendu (ex. project-wizard / subscription-start):
        - "Voyage avec enfants mineurs: Oui"
        - "Nombre d'enfants mineurs: N"
        - "  Enfant 1: Prénom Nom (né(e) le DD/MM/YYYY)"
        Retourne une liste de dicts avec clés: nom_complet, date_naissance.
        """
        import re
        if not notes:
            return []
        if not re.search(r"Voyage avec enfants mineurs\s*:\s*Oui", notes, re.IGNORECASE):
            return []
        minors = []
        # Lignes du type "  Enfant 1: Prénom Nom (né(e) le DD/MM/YYYY)"
        pattern = re.compile(
            r"^\s*Enfant\s+\d+\s*:\s*(.+?)\s*\(né\(e\)\s+le\s+([^)]+)\)",
            re.IGNORECASE | re.MULTILINE,
        )
        for match in pattern.finditer(notes):
            nom_complet = (match.group(1) or "").strip()
            date_naissance = (match.group(2) or "").strip()
            if nom_complet or date_naissance:
                minors.append({"nom_complet": nom_complet, "date_naissance": date_naissance})
        return minors

    @staticmethod
    def _decode_photo_payload(photo_payload, souscription_id: int, source: str = "questionnaire") -> Optional[bytes]:
        """Extrait et décode les données binaires d'une photo (data URL ou base64)."""
        raw_data = None
        if isinstance(photo_payload, str):
            if "base64," in photo_payload:
                raw_data = photo_payload.split("base64,", 1)[1]
            else:
                raw_data = photo_payload
        elif isinstance(photo_payload, dict):
            data_url = photo_payload.get("dataUrl") or photo_payload.get("data_url") or photo_payload.get("dataURL")
            base64_payload = photo_payload.get("base64") or photo_payload.get("base64Data")
            if data_url and "base64," in data_url:
                raw_data = data_url.split("base64,", 1)[1]
            elif base64_payload:
                raw_data = base64_payload
        if not raw_data:
            return None
        try:
            return b64decode(raw_data)
        except Exception as error:
            logger.warning(
                "Impossible de décoder la photo (%s) pour la souscription %s: %s",
                source, souscription_id, error,
            )
            return None

    @staticmethod
    def _extract_identity_photo_bytes(db: Session, souscription_id: int) -> Optional[bytes]:
        """Récupère la photo pour la carte : priorité questionnaire médical (photo medicale), puis administratif (photo identité)."""
        # 1) Priorité : photo médicale du questionnaire médical (souscription)
        questionnaire_medical = (
            db.query(Questionnaire)
            .filter(
                Questionnaire.souscription_id == souscription_id,
                Questionnaire.type_questionnaire == "medical",
            )
            .order_by(Questionnaire.version.desc())
            .first()
        )
        if questionnaire_medical and questionnaire_medical.reponses:
            photo_payload = (
                questionnaire_medical.reponses.get("photoMedicale") or
                questionnaire_medical.reponses.get("photo_medicale")
            )
            if photo_payload:
                decoded = AttestationService._decode_photo_payload(photo_payload, souscription_id, "medical")
                if decoded:
                    return decoded

        # 2) Fallback : questionnaire administratif (photo identité)
        questionnaire = (
            db.query(Questionnaire)
            .filter(
                Questionnaire.souscription_id == souscription_id,
                Questionnaire.type_questionnaire == "administratif",
            )
            .order_by(Questionnaire.version.desc())
            .first()
        )

        if not questionnaire or not questionnaire.reponses:
            logger.warning(
                "Aucun questionnaire administratif trouvé pour la souscription %s",
                souscription_id
            )
            return None

        # Log pour debug
        logger.info(
            "Extraction photo pour souscription %s: questionnaire trouvé, clés disponibles: %s",
            souscription_id,
            list(questionnaire.reponses.keys()) if questionnaire.reponses else "aucune"
        )

        # Essayer plusieurs chemins possibles pour la photo
        personal = questionnaire.reponses.get("personal") or {}
        technical = questionnaire.reponses.get("technical") or {}
        
        # Chercher la photo dans différents emplacements possibles
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
            logger.warning(
                "Aucune photo d'identité trouvée dans le questionnaire pour la souscription %s. "
                "Chemins vérifiés: personal.photoIdentity, technical.photoIdentity, photoIdentity. "
                "Structure disponible: %s",
                souscription_id,
                list(questionnaire.reponses.keys()) if questionnaire.reponses else "aucune"
            )
            return None

        decoded = AttestationService._decode_photo_payload(photo_payload, souscription_id, "administratif")
        if decoded:
            logger.info(
                "Photo d'identité décodée avec succès pour la souscription %s, taille: %d bytes",
                souscription_id,
                len(decoded),
            )
        return decoded

