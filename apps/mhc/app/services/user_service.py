"""
Service pour la gestion des utilisateurs
"""
import re
from urllib.parse import quote
from typing import Optional, Tuple
from sqlalchemy import inspect, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.user import User
from app.models.souscription import Souscription
from app.models.paiement import Paiement
from app.models.finance_refund import Refund
from app.models.finance_account import Account
from app.models.alerte import Alerte
from app.models.sinistre import Sinistre
from app.models.hospital_stay import HospitalStay
from app.models.invoice import Invoice, InvoiceItem, InvoiceHistory
from app.models.rapport import Rapport
from app.models.prestation import Prestation
from app.models.audit import AuditLog
from app.core.enums import Role
from app.core.security import (
    get_password_hash,
    create_inscription_activation_token,
    create_email_verification_token,
)
from app.core.config import settings
from app.workers.tasks import send_email
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Service pour gérer les opérations sur les utilisateurs"""
    
    # Constantes de validation
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, Optional[str]]:
        """
        Valider la force du mot de passe.
        
        Args:
            password: Mot de passe à valider
            
        Returns:
            Tuple (is_valid, error_message)
        """
        if len(password) < UserService.MIN_PASSWORD_LENGTH:
            return False, f"Le mot de passe doit contenir au moins {UserService.MIN_PASSWORD_LENGTH} caractères"
        
        if len(password) > UserService.MAX_PASSWORD_LENGTH:
            return False, f"Le mot de passe ne peut pas dépasser {UserService.MAX_PASSWORD_LENGTH} caractères"
        
        # Vérifier la complexité (au moins une lettre et un chiffre)
        has_letter = bool(re.search(r'[a-zA-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        
        if not has_letter or not has_digit:
            return False, "Le mot de passe doit contenir au moins 8 caractères, au moins une lettre (a-z) et au moins un chiffre."
        
        return True, None
    
    @staticmethod
    def check_email_exists(db: Session, email: str) -> bool:
        """Vérifier si un email existe déjà"""
        return db.query(User).filter(User.email == email).first() is not None
    
    @staticmethod
    def check_username_exists(db: Session, username: str) -> bool:
        """Vérifier si un nom d'utilisateur existe déjà"""
        return db.query(User).filter(User.username == username).first() is not None
    
    @staticmethod
    def create_user(
        db: Session,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        date_naissance: Optional[str] = None,  # Format ISO: YYYY-MM-DD
        telephone: Optional[str] = None,
        sexe: Optional[str] = None,  # 'M', 'F', 'Autre'
        pays_residence: Optional[str] = None,
        nationalite: Optional[str] = None,
        numero_passeport: Optional[str] = None,
        validite_passeport: Optional[str] = None,  # Format ISO: YYYY-MM-DD
        nom_contact_urgence: Optional[str] = None,
        contact_urgence: Optional[str] = None,
        role: Role = Role.USER,
        is_active: bool = True,
        role_id: Optional[int] = None,
        hospital_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        send_welcome_email: bool = True,
        maladies_chroniques: Optional[str] = None,
        traitements_en_cours: Optional[str] = None,
        antecedents_recents: Optional[str] = None,
        grossesse: Optional[bool] = None,
    ) -> User:
        """
        Créer un nouvel utilisateur avec validation complète.
        
        Args:
            db: Session de base de données
            email: Email de l'utilisateur
            username: Nom d'utilisateur
            password: Mot de passe en clair
            full_name: Nom complet (optionnel)
            role: Rôle de l'utilisateur (par défaut USER)
            is_active: Si l'utilisateur est actif (par défaut True)
            role_id: ID du rôle personnalisé (optionnel)
            hospital_id: ID de l'hôpital associé (optionnel)
            created_by_id: ID de l'utilisateur qui crée ce compte (None pour auto-inscription)
            send_welcome_email: Envoyer un email de bienvenue (par défaut True)
            
        Returns:
            User créé
            
        Raises:
            HTTPException: En cas d'erreur de validation
        """
        # Validation de l'email
        if UserService.check_email_exists(db, email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà enregistré"
            )
        
        # Validation du nom d'utilisateur
        if UserService.check_username_exists(db, username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom d'utilisateur est déjà pris"
            )
        
        # Validation du mot de passe
        is_valid, error_message = UserService.validate_password(password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Hash du mot de passe
        hashed_password = get_password_hash(password)
        
        # Conversion de la date de naissance si fournie
        date_naissance_obj = None
        if date_naissance:
            try:
                from datetime import datetime
                date_naissance_obj = datetime.strptime(date_naissance, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Format de date invalide. Utilisez YYYY-MM-DD"
                )

        validite_passeport_obj = None
        if validite_passeport:
            try:
                from datetime import datetime
                validite_passeport_obj = datetime.strptime(validite_passeport, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Format de validité passeport invalide. Utilisez YYYY-MM-DD"
                )
        
        # Validation du sexe si fourni
        if sexe and sexe not in ['M', 'F', 'Autre']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le sexe doit être 'M', 'F' ou 'Autre'"
            )
        
        # Auto-inscription : activation du compte après vérification e-mail (sans validation médecin MH)
        is_auto_inscription = created_by_id is None
        email_verified = False if is_auto_inscription else True
        validation_inscription = "approved"

        # Création de l'utilisateur
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            date_naissance=date_naissance_obj,
            telephone=telephone,
            sexe=sexe,
            pays_residence=pays_residence,
            nationalite=nationalite,
            numero_passeport=numero_passeport,
            validite_passeport=validite_passeport_obj,
            nom_contact_urgence=nom_contact_urgence,
            contact_urgence=contact_urgence,
            role=role,
            is_active=is_active,
            is_superuser=role == Role.ADMIN,
            role_id=role_id,
            hospital_id=hospital_id,
            created_by_id=created_by_id,
            email_verified=email_verified,
            validation_inscription=validation_inscription,
            maladies_chroniques=maladies_chroniques,
            traitements_en_cours=traitements_en_cours,
            antecedents_recents=antecedents_recents,
            grossesse=grossesse,
        )
        
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Envoyer l'email de bienvenue de manière asynchrone
            if send_welcome_email:
                try:
                    UserService.send_welcome_email(user)
                except Exception as e:
                    # Ne pas faire échouer la création si l'email échoue
                    logger.error(f"Erreur lors de l'envoi de l'email de bienvenue: {str(e)}")
            
            logger.info(f"Utilisateur créé avec succès: {username} ({email})")
            return user
            
        except Exception as e:
            db.rollback()
            error_msg = str(e)
            logger.error(f"Erreur lors de la création de l'utilisateur: {error_msg}")
            logger.exception(e)  # Log la trace complète pour le débogage
            
            # Message d'erreur plus détaillé pour les erreurs SQL
            if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                if "email" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cet email est déjà enregistré"
                    )
                elif "username" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Ce nom d'utilisateur est déjà pris"
                    )
            
            # Pour les autres erreurs, retourner un message générique mais loguer les détails
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la création du compte utilisateur: {error_msg}"
            )

    @staticmethod
    def _role_value(user: User) -> str:
        r = user.role
        if r is None:
            return ""
        if hasattr(r, "value"):
            return str(r.value).lower()
        return str(r).lower()

    @staticmethod
    def _db_has_table(db: Session, table_name: str) -> bool:
        """True si la table existe (schéma par défaut). Évite les 500 si une migration n’a pas été appliquée."""
        try:
            return bool(inspect(db.get_bind()).has_table(table_name))
        except Exception:
            return False

    @staticmethod
    def _purge_user_sos_billing_reports(db: Session, user_id: int, sub_ids: list) -> None:
        """
        Supprime les données métier liées à l'utilisateur que la base ne retire pas seule
        (FK en SET NULL : factures, rapports, prestations, séjours une fois sinistre supprimé).
        Ordre : factures liées aux séjours → rapports / prestations → sinistres → alertes SOS.
        Ignore les tables absentes (BDD partiellement migrée, ex. pas de table rapports).
        """
        has_alertes = UserService._db_has_table(db, "alertes")
        has_sinistres = UserService._db_has_table(db, "sinistres")
        has_stays = UserService._db_has_table(db, "hospital_stays")
        has_invoices = UserService._db_has_table(db, "invoices")
        has_inv_items = UserService._db_has_table(db, "invoice_items")
        has_inv_hist = UserService._db_has_table(db, "invoice_history")
        has_rapports = UserService._db_has_table(db, "rapports")
        has_prestations = UserService._db_has_table(db, "prestations")
        has_audit = UserService._db_has_table(db, "audit_logs")

        alert_ids: list = []
        if has_alertes:
            alert_ids = [r[0] for r in db.query(Alerte.id).filter(Alerte.user_id == user_id).all()]

        sinistre_ids: set = set()
        if has_sinistres:
            if alert_ids:
                sinistre_ids.update(
                    r[0] for r in db.query(Sinistre.id).filter(Sinistre.alerte_id.in_(alert_ids)).all()
                )
            if sub_ids:
                sinistre_ids.update(
                    r[0] for r in db.query(Sinistre.id).filter(Sinistre.souscription_id.in_(sub_ids)).all()
                )
        sinistre_list = list(sinistre_ids)

        stay_ids: set = set()
        if has_stays:
            if sinistre_list:
                stay_ids.update(
                    r[0]
                    for r in db.query(HospitalStay.id)
                    .filter(HospitalStay.sinistre_id.in_(sinistre_list))
                    .all()
                )
            stay_ids.update(
                r[0] for r in db.query(HospitalStay.id).filter(HospitalStay.patient_id == user_id).all()
            )
        stay_list = list(stay_ids)

        if stay_list and has_invoices:
            inv_ids = [
                r[0] for r in db.query(Invoice.id).filter(Invoice.hospital_stay_id.in_(stay_list)).all()
            ]
            if inv_ids:
                if has_inv_items:
                    db.query(InvoiceItem).filter(InvoiceItem.invoice_id.in_(inv_ids)).delete(
                        synchronize_session=False
                    )
                if has_inv_hist:
                    db.query(InvoiceHistory).filter(InvoiceHistory.invoice_id.in_(inv_ids)).delete(
                        synchronize_session=False
                    )
                db.query(Invoice).filter(Invoice.id.in_(inv_ids)).delete(synchronize_session=False)

        if has_rapports:
            if sinistre_list:
                db.query(Rapport).filter(Rapport.sinistre_id.in_(sinistre_list)).delete(
                    synchronize_session=False
                )
            db.query(Rapport).filter(Rapport.user_id == user_id).delete(synchronize_session=False)

        if has_prestations:
            if sinistre_list:
                db.query(Prestation).filter(Prestation.sinistre_id.in_(sinistre_list)).delete(
                    synchronize_session=False
                )
            db.query(Prestation).filter(Prestation.user_id == user_id).delete(synchronize_session=False)

        if sinistre_list and has_sinistres:
            db.query(Sinistre).filter(Sinistre.id.in_(sinistre_list)).delete(synchronize_session=False)

        if has_alertes:
            db.query(Alerte).filter(Alerte.user_id == user_id).delete(synchronize_session=False)

        if has_audit:
            db.query(AuditLog).filter(AuditLog.user_id == user_id).delete(synchronize_session=False)

    @staticmethod
    def delete_user_cascade(db: Session, user_id: int, acting_user_id: int) -> None:
        """
        Supprime un utilisateur et tout ce qui le concerne : alertes SOS, sinistres, séjours,
        factures (lignes + historique), rapports, prestations, journaux d'audit, puis
        remboursements / comptes financiers bloquants, enfin souscriptions, projets,
        attestations, paiements, notifications, etc. (CASCADE SQL + ORM).
        """
        if user_id == acting_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous ne pouvez pas supprimer votre propre compte.",
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if UserService._role_value(user) == Role.ADMIN.value:
            other_admins = (
                db.query(User)
                .filter(User.id != user_id)
                .filter(User.role == Role.ADMIN)
                .count()
            )
            if other_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Impossible de supprimer le dernier administrateur.",
                )

        sub_ids = [row[0] for row in db.query(Souscription.id).filter(Souscription.user_id == user_id).all()]
        pay_ids = [row[0] for row in db.query(Paiement.id).filter(Paiement.user_id == user_id).all()]

        UserService._purge_user_sos_billing_reports(db, user_id, sub_ids)

        if sub_ids or pay_ids:
            refund_conds = []
            if sub_ids:
                refund_conds.append(Refund.souscription_id.in_(sub_ids))
            if pay_ids:
                refund_conds.append(Refund.paiement_id.in_(pay_ids))
            db.query(Refund).filter(or_(*refund_conds)).delete(synchronize_session=False)

        for acc in db.query(Account).filter(Account.owner_id == user_id).all():
            db.query(Refund).filter(Refund.account_id == acc.id).delete(synchronize_session=False)
            db.delete(acc)

        # DELETE SQL direct : évite de charger les relations ORM (contacts_proches, etc.)
        # si la table correspondante n’existe pas encore sur une BDD partiellement migrée.
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            logger.exception("Suppression utilisateur %s: contrainte SQL", user_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Impossible de supprimer cet utilisateur : des données liées empêchent la suppression. "
                "Vérifiez les remboursements, factures ou autres enregistrements associés.",
            ) from e
    
    @staticmethod
    def send_welcome_email(user: User):
        """
        Envoyer un email de bienvenue à un nouvel utilisateur.
        
        Args:
            user: Utilisateur à qui envoyer l'email
        """
        subject = "Bienvenue sur Mobility Health"
        
        # Contenu HTML de l'email
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Bienvenue sur Mobility Health</h1>
                </div>
                <div class="content">
                    <p>Bonjour {user.full_name or user.username},</p>
                    
                    <p>Votre compte a été créé avec succès sur la plateforme Mobility Health.</p>
                    
                    <p><strong>Informations de connexion :</strong></p>
                    <ul>
                        <li><strong>Nom d'utilisateur :</strong> {user.username}</li>
                        <li><strong>Email :</strong> {user.email}</li>
                    </ul>
                    
                    <p>Vous pouvez maintenant vous connecter à votre compte et commencer à utiliser nos services.</p>
                    
                    <p>Si vous avez des questions ou besoin d'aide, n'hésitez pas à nous contacter.</p>
                    
                    <p>Cordialement,<br>L'équipe Mobility Health</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Contenu texte simple
        body_text = f"""
        Bienvenue sur Mobility Health
        
        Bonjour {user.full_name or user.username},
        
        Votre compte a été créé avec succès sur la plateforme Mobility Health.
        
        Informations de connexion :
        - Nom d'utilisateur : {user.username}
        - Email : {user.email}
        
        Vous pouvez maintenant vous connecter à votre compte et commencer à utiliser nos services.
        
        Si vous avez des questions ou besoin d'aide, n'hésitez pas à nous contacter.
        
        Cordialement,
        L'équipe Mobility Health
        """
        
        # Envoyer l'email via Celery
        send_email.delay(
            to_email=user.email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            user_id=user.id
        )
        
        logger.info(f"Email de bienvenue envoyé à {user.email}")
    
    @staticmethod
    def send_verification_email(user: User, verification_code: str):
        """
        Envoyer un email de vérification à un nouvel utilisateur.
        
        Args:
            user: Utilisateur à qui envoyer l'email
            verification_code: Code de vérification à 6 chiffres
        """
        subject = "Vérifiez votre email - Mobility Health"

        site_base = (getattr(settings, "ASSURANCE_SITE_WEB", "") or "").strip().rstrip("/")
        link_token = create_email_verification_token(user.id, user.email)
        verify_link = (
            f"{site_base}/api/v1/auth/verify-email-link?token={quote(link_token, safe='')}"
            if site_base
            else ""
        )
        
        # Contenu HTML de l'email
        link_block = ""
        if verify_link:
            link_block = f"""
                    <p style="text-align:center;margin:24px 0;">
                        <a href="{verify_link}" style="display:inline-block;padding:14px 28px;background-color:#4CAF50;color:#ffffff !important;text-decoration:none;border-radius:6px;font-weight:bold;">
                            Activer mon compte
                        </a>
                    </p>
                    <p style="font-size:14px;color:#666;">Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br><span style="word-break:break-all;">{verify_link}</span></p>
                    <p style="margin-top:20px;">Vous pouvez aussi saisir le code ci-dessous sur la page de vérification :</p>
            """
        else:
            link_block = """
                    <p>Pour activer votre compte, saisissez le code ci-dessous sur la page de vérification du site.</p>
            """

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .code {{
                    background-color: #fff;
                    border: 2px solid #4CAF50;
                    border-radius: 5px;
                    padding: 20px;
                    text-align: center;
                    font-size: 32px;
                    font-weight: bold;
                    color: #4CAF50;
                    letter-spacing: 8px;
                    margin: 20px 0;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Vérification de votre email</h1>
                </div>
                <div class="content">
                    <p>Bonjour {user.full_name or user.username},</p>
                    
                    <p>Merci de vous être inscrit sur Mobility Health. Pour activer votre compte, vous pouvez cliquer sur le bouton ci-dessous (méthode recommandée) :</p>
                    {link_block}
                    
                    <div class="code">{verification_code}</div>
                    
                    <div class="warning">
                        <strong>⚠️ Important :</strong> Ce lien et ce code sont valides pendant 15 minutes uniquement.
                    </div>
                    
                    <p>Si vous n'avez pas créé de compte sur Mobility Health, vous pouvez ignorer cet email.</p>
                    
                    <p>Cordialement,<br>L'équipe Mobility Health</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Contenu texte simple
        link_line = f"\nLien pour activer votre compte (cliquez ou copiez dans le navigateur) :\n{verify_link}\n" if verify_link else ""
        body_text = f"""
        Vérification de votre email - Mobility Health
        
        Bonjour {user.full_name or user.username},
        
        Merci de vous être inscrit sur Mobility Health.{link_line}
        Vous pouvez aussi utiliser ce code de vérification sur le site :
        
        {verification_code}
        
        ⚠️ Important : Ce lien et ce code sont valides pendant 15 minutes uniquement.
        
        Si vous n'avez pas créé de compte sur Mobility Health, vous pouvez ignorer cet email.
        
        Cordialement,
        L'équipe Mobility Health
        """
        
        # Envoyer l'email via Celery
        send_email.delay(
            to_email=user.email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            user_id=user.id
        )
        
        logger.info(f"Email de vérification envoyé à {user.email}")

    @staticmethod
    def send_inscription_approval_email(user: User):
        """Envoyer l'email d'approbation avec lien d'activation finale."""
        activation_token = create_inscription_activation_token(user.id)
        site_base = (getattr(settings, "ASSURANCE_SITE_WEB", "") or "").strip().rstrip("/")
        activation_link = f"{site_base}/api/v1/auth/confirm-inscription?token={activation_token}" if site_base else ""

        subject = "Votre inscription a été approuvée - Activation finale"
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #0d9488; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #0d9488; color: #fff !important; text-decoration: none; border-radius: 6px; font-weight: bold; }}
                .info {{ background-color: #ecfeff; border-left: 4px solid #0d9488; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Inscription approuvée</h1>
                </div>
                <div class="content">
                    <p>Bonjour {user.full_name or user.username},</p>
                    <p>Votre inscription a été validée par l'équipe médicale Mobility Health.</p>
                    <p>Pour activer définitivement votre compte et pouvoir vous connecter sur l'application mobile, cliquez sur le lien ci-dessous :</p>
                    <p><a class="button" href="{activation_link}">Activer mon compte</a></p>
                    <div class="info">
                        <strong>Important :</strong> ce lien active votre compte. Une fois l'activation effectuée, vous pourrez vous connecter sur l'application mobile avec vos identifiants.
                    </div>
                    <p>Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :</p>
                    <p style="word-break: break-all;">{activation_link}</p>
                    <p>Cordialement,<br>L'équipe Mobility Health</p>
                </div>
            </div>
        </body>
        </html>
        """
        body_text = f"""
        Bonjour {user.full_name or user.username},

        Votre inscription a été validée par l'équipe médicale Mobility Health.

        Pour activer définitivement votre compte et pouvoir vous connecter sur l'application mobile, ouvrez ce lien :
        {activation_link}

        Une fois l'activation effectuée, vous pourrez vous connecter sur l'application mobile avec vos identifiants.

        Cordialement,
        L'équipe Mobility Health
        """
        send_email.delay(
            to_email=user.email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            user_id=user.id
        )
        logger.info(f"Email d'activation finale envoyé à {user.email}")

    @staticmethod
    def send_inscription_rejection_email(user: User, notes: Optional[str] = None):
        """Envoyer l'email de refus d'inscription."""
        subject = "Votre inscription Mobility Health a été refusée"
        note_block_html = f"<p><strong>Motif / observation :</strong> {notes}</p>" if notes else ""
        note_block_text = f"\nMotif / observation : {notes}\n" if notes else "\n"
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc2626; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Inscription refusée</h1>
                </div>
                <div class="content">
                    <p>Bonjour {user.full_name or user.username},</p>
                    <p>Nous vous informons que votre demande d'inscription a été refusée après étude de votre dossier.</p>
                    {note_block_html}
                    <p>Si vous souhaitez plus d'informations, merci de contacter le service client Mobility Health.</p>
                    <p>Cordialement,<br>L'équipe Mobility Health</p>
                </div>
            </div>
        </body>
        </html>
        """
        body_text = f"""
        Bonjour {user.full_name or user.username},

        Nous vous informons que votre demande d'inscription a été refusée après étude de votre dossier.
        {note_block_text}
        Si vous souhaitez plus d'informations, merci de contacter le service client Mobility Health.

        Cordialement,
        L'équipe Mobility Health
        """
        send_email.delay(
            to_email=user.email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            user_id=user.id
        )
        logger.info(f"Email de refus d'inscription envoyé à {user.email}")
    
    @staticmethod
    def send_password_reset_email(user: User, reset_code: str):
        """
        Envoyer un email de réinitialisation de mot de passe.
        
        Args:
            user: Utilisateur à qui envoyer l'email
            reset_code: Code de réinitialisation à 6 chiffres
        """
        subject = "Réinitialisation de votre mot de passe - Mobility Health"
        
        # Contenu HTML de l'email
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .code {{
                    background-color: #fff;
                    border: 2px solid #4CAF50;
                    border-radius: 5px;
                    padding: 20px;
                    text-align: center;
                    font-size: 32px;
                    font-weight: bold;
                    color: #4CAF50;
                    letter-spacing: 8px;
                    margin: 20px 0;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Réinitialisation de mot de passe</h1>
                </div>
                <div class="content">
                    <p>Bonjour {user.full_name or user.username},</p>
                    
                    <p>Vous avez demandé la réinitialisation de votre mot de passe sur Mobility Health. Veuillez utiliser le code ci-dessous pour continuer :</p>
                    
                    <div class="code">{reset_code}</div>
                    
                    <div class="warning">
                        <strong>⚠️ Important :</strong> Ce code est valide pendant 10 minutes uniquement.
                    </div>
                    
                    <p>Si vous n'avez pas demandé de réinitialisation de mot de passe, ignorez cet email. Votre mot de passe restera inchangé.</p>
                    
                    <p>Cordialement,<br>L'équipe Mobility Health</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Contenu texte simple
        body_text = f"""
        Réinitialisation de votre mot de passe - Mobility Health
        
        Bonjour {user.full_name or user.username},
        
        Vous avez demandé la réinitialisation de votre mot de passe sur Mobility Health. Veuillez utiliser le code suivant :
        
        {reset_code}
        
        ⚠️ Important : Ce code est valide pendant 10 minutes uniquement.
        
        Si vous n'avez pas demandé de réinitialisation de mot de passe, ignorez cet email. Votre mot de passe restera inchangé.
        
        Cordialement,
        L'équipe Mobility Health
        """
        
        # Envoyer l'email via Celery
        send_email.delay(
            to_email=user.email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            user_id=user.id
        )
        
        logger.info(f"Email de réinitialisation de mot de passe envoyé à {user.email}")

