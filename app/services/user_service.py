"""
Service pour la gestion des utilisateurs
"""
import re
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.core.enums import Role
from app.core.security import get_password_hash
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
        
        if not has_letter:
            return False, "Le mot de passe doit contenir au moins une lettre"
        
        if not has_digit:
            return False, "Le mot de passe doit contenir au moins un chiffre"
        
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
        
        # Auto-inscription : en attente de validation par le médecin MH (email_verified + validation_inscription)
        is_auto_inscription = created_by_id is None
        email_verified = False if is_auto_inscription else True
        validation_inscription = "pending" if is_auto_inscription else "approved"

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
                    <h1>Vérification de votre email</h1>
                </div>
                <div class="content">
                    <p>Bonjour {user.full_name or user.username},</p>
                    
                    <p>Merci de vous être inscrit sur Mobility Health. Pour activer votre compte, veuillez utiliser le code de vérification ci-dessous :</p>
                    
                    <div class="code">{verification_code}</div>
                    
                    <div class="warning">
                        <strong>⚠️ Important :</strong> Ce code est valide pendant 15 minutes uniquement.
                    </div>
                    
                    <p>Si vous n'avez pas créé de compte sur Mobility Health, vous pouvez ignorer cet email.</p>
                    
                    <p>Cordialement,<br>L'équipe Mobility Health</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Contenu texte simple
        body_text = f"""
        Vérification de votre email - Mobility Health
        
        Bonjour {user.full_name or user.username},
        
        Merci de vous être inscrit sur Mobility Health. Pour activer votre compte, veuillez utiliser le code de vérification suivant :
        
        {verification_code}
        
        ⚠️ Important : Ce code est valide pendant 15 minutes uniquement.
        
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

