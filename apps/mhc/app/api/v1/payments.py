from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from app.core.database import get_db
from app.core.enums import StatutPaiement, StatutSouscription, TypePaiement, Role
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.paiement import Paiement
from app.models.souscription import Souscription
from app.models.produit_assurance import ProduitAssurance
from app.models.assureur import Assureur
from app.models.assureur_agent import AssureurAgent
from app.models.courtier import Courtier
from app.models.projet_voyage import ProjetVoyage
from app.models.questionnaire import Questionnaire
from app.models.finance_refund import Refund
from pydantic import BaseModel, Field, ConfigDict
from app.services.attestation_service import AttestationService
from app.services.notification_service import NotificationService
from app.services.prime_tarif_service import resolve_prime_tarif_detail
from app.schemas.paiement import AccountingTransaction
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_medical_photo_required(medical_form: Dict[str, Any]) -> None:
    """Exige une photo décodable pour la e-carte (champs questionnaire médical)."""
    msg = AttestationService.validate_identity_photo_in_medical_reponses(medical_form)
    if msg:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


ACCOUNTANT_ROLES = {
    Role.AGENT_COMPTABLE_MH,
    Role.AGENT_COMPTABLE_ASSUREUR,
    Role.AGENT_COMPTABLE_COURTIER,
    Role.FINANCE_MANAGER,
    Role.ADMIN,
}


def require_accountant_role(current_user: User) -> User:
    if current_user.role not in ACCOUNTANT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Accounting role required.",
        )


def _get_assureur_scope_for_accountant(db: Session, current_user: User) -> Optional[set[int]]:
    """Assure la rétrocompatibilité entre le champ direct et la liaison multi-agents."""
    if current_user.role != Role.AGENT_COMPTABLE_ASSUREUR:
        return None

    assureur_ids = {
        row[0]
        for row in db.query(Assureur.id)
        .filter(Assureur.agent_comptable_id == current_user.id)
        .all()
    }

    try:
        assureur_ids.update(
            row[0]
            for row in db.query(AssureurAgent.assureur_id)
            .filter(
                AssureurAgent.user_id == current_user.id,
                AssureurAgent.type_agent == "comptable",
            )
            .all()
        )
    except Exception:
        logger.exception("Impossible de résoudre le scope assureur via AssureurAgent")

    return assureur_ids


def _get_courtier_scope_for_accountant(db: Session, current_user: User) -> Optional[set[int]]:
    if current_user.role != Role.AGENT_COMPTABLE_COURTIER:
        return None
    return {
        row[0]
        for row in db.query(Courtier.id).filter(Courtier.agent_comptable_id == current_user.id).all()
    }


def _ledger_prime_and_frais_split(
    subscription: Optional[Souscription],
    montant_total: Decimal,
) -> Tuple[Decimal, Decimal]:
    """
    Répartition comptable des encaissements souscription : part assureur = prime d'assurance,
    Mobility Health = frais de services (plus de pourcentage sur le total payé).
    """
    mt = montant_total or Decimal("0.00")
    if not subscription:
        return mt.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), Decimal("0.00")

    prime = subscription.prime_assurance
    frais = subscription.frais_services

    if prime is not None and frais is not None:
        part_ass = Decimal(str(prime)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        part_mh = Decimal(str(frais)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return part_ass, part_mh

    if prime is not None:
        part_ass = Decimal(str(prime)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        part_mh = (mt - part_ass).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return part_ass, part_mh if part_mh > 0 else Decimal("0.00")

    if frais is not None:
        part_mh = Decimal(str(frais)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        part_ass = (mt - part_mh).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return part_ass if part_ass > 0 else Decimal("0.00"), part_mh

    # Anciennes souscriptions sans détail : tout le paiement compte comme prime assureur
    return mt.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), Decimal("0.00")


def _ledger_with_optional_courtier(
    subscription: Optional[Souscription],
    montant_total: Decimal,
    db: Session,
    assureur_id: Optional[int] = None,
) -> Tuple[Decimal, Decimal, Decimal, Optional[int], Optional[str], Optional[Decimal]]:
    """
    Retourne (assureur, mh, courtier, courtier_id, courtier_nom, commission_pct).
    commission courtier appliquée sur la prime d'assurance uniquement.
    """
    assureur_share, mh_share = _ledger_prime_and_frais_split(subscription, montant_total)
    if not subscription:
        return assureur_share, mh_share, Decimal("0.00"), None, None, None

    courtier = None
    courtier_id = getattr(subscription, "courtier_id", None)
    if courtier_id:
        courtier = db.query(Courtier).filter(Courtier.id == courtier_id).first()
    elif assureur_id:
        # Fallback legacy: certaines souscriptions historiques n'ont pas courtier_id.
        # On rattache alors le courtier du même assureur (premier id pour stabilité).
        matches = (
            db.query(Courtier)
            .filter(Courtier.assureur_id == assureur_id)
            .order_by(Courtier.id.asc())
            .all()
        )
        if len(matches) == 1:
            courtier = matches[0]
        elif len(matches) > 1:
            courtier = matches[0]
            logger.warning(
                "Plusieurs courtiers trouvés pour assureur_id=%s, fallback sur id=%s",
                assureur_id,
                courtier.id,
            )

    if not courtier:
        return assureur_share, mh_share, Decimal("0.00"), None, None, None
    pct = Decimal(str(courtier.commission_pct or Decimal("0.00")))
    courtier_share = (assureur_share * (pct / Decimal("100"))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    assureur_share = (assureur_share - courtier_share).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return assureur_share, mh_share, courtier_share, courtier.id, courtier.nom, pct


def _refund_policy_breakdown(
    subscription: Optional[Souscription],
    montant_total: Decimal,
    refund_kind: str,
) -> Tuple[Decimal, Decimal]:
    """
    Retourne (montant_rembourse_assure, montant_conserve_mh).

    Règles métier:
    - refus dossier: assureur + courtier remboursent intégralement, MH conserve ses frais de service.
    - résiliation: assureur + courtier remboursent intégralement, MH perçoit 30 % de la prime.
    """
    mt = (montant_total or Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    prime_share, frais_share = _ledger_prime_and_frais_split(subscription, mt)

    has_explicit_breakdown = bool(
        subscription
        and (
            getattr(subscription, "prime_assurance", None) is not None
            or getattr(subscription, "frais_services", None) is not None
        )
    )

    if refund_kind == "resiliation":
        mh_retained = (prime_share * Decimal("0.30")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        mh_retained = frais_share if has_explicit_breakdown else (
            mt * Decimal("0.10")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if mh_retained < Decimal("0.00"):
        mh_retained = Decimal("0.00")
    if mh_retained > mt:
        mh_retained = mt

    insured_refund = (mt - mh_retained).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return insured_refund, mh_retained


class PaymentInitiateRequest(BaseModel):
    subscription_id: int
    amount: Decimal = Field(..., gt=0, description="Montant du paiement")
    payment_type: str = "carte_bancaire"


class PaymentInitiateResponse(BaseModel):
    payment_id: int
    payment_url: str
    status: str
    
    class Config:
        from_attributes = True


class PaymentWebhookRequest(BaseModel):
    payment_id: int
    external_reference: str
    status: str  # "success", "failed", "pending"
    amount: Optional[Decimal] = None


class PaymentStatusResponse(BaseModel):
    payment_id: int
    status: str
    amount: Decimal
    subscription_id: int
    subscription_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaymentCheckoutRequest(BaseModel):
    project_id: int
    produit_assurance_id: int
    payment_method: TypePaiement = TypePaiement.CARTE_BANCAIRE
    administrative_form: Dict[str, Any]
    medical_form: Dict[str, Any]
    # Caractéristiques pour tarif selon durée, zone et âge (sinon prix de base)
    destination_country_id: Optional[int] = None
    destination_country_name: Optional[str] = None
    zone_code: Optional[str] = None
    duree_jours: Optional[int] = None
    age: Optional[int] = None  # Si absent, calculé depuis l'utilisateur connecté (date_naissance)


class PaymentCheckoutResponse(BaseModel):
    subscription_id: int
    numero_souscription: str
    payment_id: int
    payment_status: StatutPaiement
    amount: Decimal
    attestation_id: int
    attestation_number: str
    attestation_url: Optional[str]

    class Config:
        from_attributes = True


class PaymentConfirmRequest(BaseModel):
    """Accepte subscription_id (mobile) ou souscription_id (web)."""
    souscription_id: int = Field(..., alias="subscription_id", description="ID de la souscription")
    montant: Decimal = Field(..., gt=0, description="Montant du paiement")
    methode_paiement: str = "carte_bancaire"

    model_config = ConfigDict(populate_by_name=True)


class PaymentConfirmResponse(BaseModel):
    payment_id: int
    payment_status: str
    subscription_id: int
    subscription_status: str
    amount: Decimal
    attestation_id: Optional[int] = None
    attestation_number: Optional[str] = None
    attestation_url: Optional[str] = None

    class Config:
        from_attributes = True


def log_transaction(
    db: Session,
    payment_id: int,
    action: str,
    details: dict,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Logger une transaction de paiement dans la base de données"""
    try:
        from app.models.transaction_log import TransactionLog
        
        log_entry = TransactionLog(
            payment_id=payment_id,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(log_entry)
        db.commit()
        
        logger.info(f"Transaction logged: payment_id={payment_id}, action={action}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error logging transaction: {e}")


def process_payment_success(
    payment_id: int,
    subscription_id: int,
    generate_attestation: bool = False
):
    """Traiter un paiement réussi avec transitions ACID"""
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Démarrer une transaction
        payment = db.query(Paiement).filter(Paiement.id == payment_id).first()
        subscription = db.query(Souscription).filter(Souscription.id == subscription_id).first()
        
        if not payment or not subscription:
            raise ValueError("Payment or subscription not found")
        
        # Transition ACID : Mettre à jour le paiement
        payment.statut = StatutPaiement.VALIDE
        payment.date_paiement = datetime.utcnow()
        
        # Transition ACID : Mettre à jour la souscription
        subscription.statut = StatutSouscription.ACTIVE

        attestation_number = None
        attestation_url = None

        if generate_attestation:
            from app.services.attestation_service import AttestationService
            from app.models.user import User

            user = db.query(User).filter(User.id == payment.user_id).first()
            if user:
                attestation = AttestationService.create_attestation_provisoire(
                    db=db,
                    souscription=subscription,
                    paiement=payment,
                    user=user
                )
                attestation_number = attestation.numero_attestation
                attestation_url = attestation.url_signee
            else:
                attestation_number = f"ATT-{subscription.numero_souscription}-{datetime.utcnow().strftime('%Y%m%d')}"

        log_transaction(
            db=db,
            payment_id=payment_id,
            action="payment_success",
            details={
                "subscription_id": subscription_id,
                "attestation_number": attestation_number,
                "amount": float(payment.montant)
            },
            user_id=payment.user_id
        )
        
        # Commit de la transaction
        db.commit()
        
        logger.info(f"Payment {payment_id} processed successfully. Attestation: {attestation_number}")
        
        if generate_attestation and attestation_number:
            try:
                from app.workers.tasks import send_email, send_sms
                from app.models.user import User

                user = db.query(User).filter(User.id == payment.user_id).first()
                if user:
                    display_name = user.full_name or user.username
                    email_subject = f"Attestation provisoire - {attestation_number}"
                    email_body_html = f"""
                    <html>
                    <body>
                        <h2>Votre attestation provisoire est prête</h2>
                        <p>Bonjour {display_name},</p>
                        <p>Votre paiement a été validé avec succès. Votre attestation provisoire est disponible.</p>
                        <p><strong>Numéro d'attestation:</strong> {attestation_number}</p>
                        <p><strong>Numéro de souscription:</strong> {subscription.numero_souscription}</p>
                        <p><strong>Montant payé:</strong> {payment.montant} FCFA</p>
                        {f'<p><a href="{attestation_url}">Télécharger votre attestation</a></p>' if attestation_url else ''}
                        <p>Cordialement,<br>L'équipe Mobility Health</p>
                    </body>
                    </html>
                    """
                    email_body_text = f"""
                    Votre attestation provisoire est prête
                    
                    Bonjour {display_name},
                    
                    Votre paiement a été validé avec succès. Votre attestation provisoire est disponible.
                    
                    Numéro d'attestation: {attestation_number}
                    Numéro de souscription: {subscription.numero_souscription}
                    Montant payé: {payment.montant} FCFA
                    
                    {f'Télécharger votre attestation: {attestation_url}' if attestation_url else ''}
                    
                    Cordialement,
                    L'équipe Mobility Health
                    """
                    
                    if user.email:
                        send_email.delay(
                            to_email=user.email,
                            subject=email_subject,
                            body_html=email_body_html,
                            body_text=email_body_text,
                            user_id=user.id
                        )
                    
                    if user.telephone:
                        sms_message = f"Votre attestation provisoire {attestation_number} est prête. Montant: {payment.montant} FCFA. Mobility Health"
                        send_sms.delay(
                            to_phone=user.telephone,
                            message=sms_message,
                            user_id=user.id
                        )
                    
                    logger.info(f"Email and SMS queued for user {user.id} for attestation {attestation_number}")
            except Exception as e:
                logger.error(f"Error queuing email/SMS for attestation: {e}")
        
        return attestation_number
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing payment {payment_id}: {e}")
        raise
    finally:
        db.close()


@router.post("/initiate", response_model=PaymentInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    request: PaymentInitiateRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouveau paiement et renvoyer l'URL de paiement"""
    # Vérifier que la souscription existe et appartient à l'utilisateur
    subscription = db.query(Souscription).filter(
        and_(
            Souscription.id == request.subscription_id,
            Souscription.user_id == current_user.id
        )
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Vérifier que la souscription n'est pas déjà payée
    if subscription.statut == StatutSouscription.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription already paid"
        )
    
    # Créer le paiement
    payment = Paiement(
        souscription_id=request.subscription_id,
        user_id=current_user.id,
        montant=request.amount,
        type_paiement=request.payment_type,
        statut=StatutPaiement.EN_ATTENTE,
        reference_transaction=f"TXN-{uuid.uuid4().hex[:16].upper()}"
    )
    
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    # Récupérer l'IP et le user agent
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    
    # Logger la création du paiement
    log_transaction(
        db=db,
        payment_id=payment.id,
        action="payment_initiated",
        details={
            "subscription_id": request.subscription_id,
            "amount": float(request.amount),
            "payment_type": request.payment_type
        },
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    # Générer l'URL de paiement (simulée)
    # En production, cela pointerait vers le provider de paiement réel
    base_url = str(http_request.base_url).rstrip('/')
    payment_url = f"{base_url}/checkout.html?payment_id={payment.id}&token={payment.reference_transaction}&amount={request.amount}&subscription_id={request.subscription_id}"
    
    return PaymentInitiateResponse(
        payment_id=payment.id,
        payment_url=payment_url,
        status=payment.statut.value
    )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def payment_webhook(
    request: PaymentWebhookRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Webhook pour recevoir les notifications du provider de paiement"""
    
    # Vérifier que le paiement existe
    payment = db.query(Paiement).filter(Paiement.id == request.payment_id).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Récupérer l'IP et le user agent
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    
    # Logger la réception du webhook
    log_transaction(
        db=db,
        payment_id=payment.id,
        action="webhook_received",
        details={
            "external_reference": request.external_reference,
            "status": request.status,
            "amount": float(request.amount) if request.amount else None
        },
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    # Traiter selon le statut
    if request.status == "success":
        # Mettre à jour la référence externe
        payment.reference_externe = request.external_reference
        payment.statut = StatutPaiement.EN_COURS
        
        db.commit()
        db.refresh(payment)
        
        # Traiter le paiement en arrière-plan avec transitions ACID
        background_tasks.add_task(
            process_payment_success,
            payment_id=payment.id,
            subscription_id=payment.souscription_id,
            generate_attestation=True
        )
        
        return {"status": "processing", "message": "Payment is being processed"}
        
    elif request.status == "failed":
        payment.statut = StatutPaiement.ECHOUE
        payment.reference_externe = request.external_reference
        
        log_transaction(
            db=db,
            payment_id=payment.id,
            action="payment_failed",
            details={
                "external_reference": request.external_reference,
                "reason": "Payment failed from provider"
            }
        )
        
        db.commit()
        return {"status": "failed", "message": "Payment failed"}
        
    else:  # pending
        payment.statut = StatutPaiement.EN_ATTENTE
        payment.reference_externe = request.external_reference
        db.commit()
        return {"status": "pending", "message": "Payment is pending"}


@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir le statut d'un paiement"""
    payment = db.query(Paiement).filter(
        and_(
            Paiement.id == payment_id,
            Paiement.user_id == current_user.id
        )
    ).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    subscription = db.query(Souscription).filter(
        Souscription.id == payment.souscription_id
    ).first()
    
    return PaymentStatusResponse(
        payment_id=payment.id,
        status=payment.statut.value,
        amount=payment.montant,
        subscription_id=payment.souscription_id,
        subscription_status=subscription.statut.value if subscription else "unknown",
        created_at=payment.created_at
    )


def _generate_subscription_number(db: Session, souscription: Optional["Souscription"] = None, country_name: Optional[str] = None) -> str:
    from app.services.mhc_reference_service import allocate_police_number
    return allocate_police_number(db, souscription=souscription, country_name=country_name)


def _upsert_questionnaire(db: Session, subscription_id: int, questionnaire_type: str, responses: Dict[str, Any]):
    if not responses:
        logger.warning(f"⚠️ _upsert_questionnaire: responses est vide pour subscription_id={subscription_id}, type={questionnaire_type}")
        return None
    
    # DEBUG: Logger le contenu pour diagnostic
    if questionnaire_type == "administratif":
        personal = responses.get("personal", {})
        logger.info(
            f"📝 Enregistrement questionnaire administratif - Souscription ID: {subscription_id}"
        )
        logger.info(
            f"📝 Keys dans responses: {list(responses.keys())}"
        )
        logger.info(
            f"📝 Personal fullName: '{personal.get('fullName', 'NOT FOUND')}'"
        )
        logger.info(
            f"📝 Personal keys: {list(personal.keys()) if personal else 'None'}"
        )
    
    existing = db.query(Questionnaire).filter(
        Questionnaire.souscription_id == subscription_id,
        Questionnaire.type_questionnaire == questionnaire_type
    ).order_by(Questionnaire.version.desc()).first()
    version = 1
    if existing:
        version = existing.version + 1
        existing.statut = "archive"
    questionnaire = Questionnaire(
        souscription_id=subscription_id,
        type_questionnaire=questionnaire_type,
        version=version,
        reponses=responses,
        statut="complete"
    )
    db.add(questionnaire)
    db.flush()
    
    logger.info(
        f"✅ Questionnaire {questionnaire_type} créé avec version {version} pour souscription {subscription_id}"
    )
    
    return questionnaire


def _notify_questionnaire_reviewers(
    db: Session,
    questionnaire: Optional[Questionnaire],
    role: Role,
    souscription: Souscription,
    label: str
):
    if not questionnaire:
        return

    reviewers = db.query(User).filter(
        User.role == role,
        User.is_active == True
    ).all()

    if not reviewers:
        logger.warning("Aucun relecteur trouvé pour le rôle %s", role.value)
        return

    for reviewer in reviewers:
        NotificationService.create_notification(
            user_id=reviewer.id,
            type_notification="questionnaire_review",
            titre=f"Questionnaire {label} à évaluer",
            message=(
                f"La souscription #{souscription.numero_souscription} a soumis son questionnaire {label}. "
                "Merci de procéder à l'évaluation."
            ),
            lien_relation_id=questionnaire.id,
            lien_relation_type="questionnaire",
            channels=["push"]
        )


def _map_transaction_action(status: StatutPaiement) -> str:
    if status == StatutPaiement.VALIDE:
        return "payé"
    if status == StatutPaiement.ECHOUE:
        return "rejeté le paiement"
    if status == StatutPaiement.REMBOURSE:
        return "rembourser"
    return "payé"


@router.post("/checkout", response_model=PaymentCheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout_payment(
    request: PaymentCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Étape 1 : Créer la souscription, enregistrer les questionnaires et confirmer le paiement.
    """
    projet = db.query(ProjetVoyage).filter(
        ProjetVoyage.id == request.project_id,
        ProjetVoyage.user_id == current_user.id
    ).first()
    if not projet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet de voyage introuvable")

    produit = db.query(ProduitAssurance).filter(
        ProduitAssurance.id == request.produit_assurance_id,
        ProduitAssurance.est_actif == True
    ).first()
    if not produit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit d'assurance introuvable ou inactif")

    _validate_medical_photo_required(request.medical_form)

    # Âge : depuis la requête ou l'utilisateur connecté (date_naissance)
    age = request.age
    if age is None and getattr(current_user, "date_naissance", None):
        birthdate = current_user.date_naissance
        if isinstance(birthdate, datetime):
            birthdate = birthdate.date() if hasattr(birthdate, "date") else birthdate
        if birthdate:
            today = date.today()
            age = (today - birthdate).days // 365

    # Durée et zone : depuis la requête ou le projet
    duree_jours = request.duree_jours
    destination_country_id = request.destination_country_id
    zone_code = request.zone_code
    if duree_jours is None and projet.date_depart and projet.date_retour:
        delta = projet.date_retour - projet.date_depart
        duree_jours = max(1, delta.days)

    # Tarif selon parcours résidence → destination, durée et âge
    td = resolve_prime_tarif_detail(
        db,
        product_id=produit.id,
        age=age,
        destination_country_id=destination_country_id,
        destination_country_name=request.destination_country_name,
        zone_code=zone_code,
        duree_jours=duree_jours,
        projet=projet,
        user_pays_residence=getattr(current_user, "pays_residence", None),
    )
    montant = td.prix

    date_debut = projet.date_depart or datetime.utcnow()
    date_fin = None
    if produit.duree_validite_jours:
        date_fin = date_debut + timedelta(days=produit.duree_validite_jours)
    elif projet.date_retour:
        date_fin = projet.date_retour

    numero_souscription = _generate_subscription_number(db, country_name=projet.destination if projet else None)

    # Construire les notes de la souscription
    subscription_notes = "Souscription générée via checkout"
    
    # IMPORTANT: La souscription est TOUJOURS créée au nom de l'utilisateur connecté (abonné)
    # même si c'est une souscription pour un tiers. Les informations du tiers sont utilisées
    # uniquement pour les documents (attestations, cartes) mais la souscription reste liée à l'abonné.
    
    # Vérifier si c'est une souscription pour un tiers
    # Les informations du tiers peuvent être dans les notes du projet ou dans le questionnaire administratif
    is_tier_subscription = False
    tier_info_from_project = ""
    if projet.notes and ("Pour un tiers" in projet.notes or "pour un tiers" in projet.notes.lower()):
        is_tier_subscription = True
        # C'est une souscription pour un tiers, extraire les informations du tiers depuis les notes du projet
        # et les ajouter dans les notes de la souscription pour référence future
        subscription_notes = f"{subscription_notes}\n\n⚠️ SOUSCRIPTION POUR UN TIERS ⚠️\n"
        subscription_notes += f"Abonné (souscripteur): {current_user.full_name or current_user.username} (ID: {current_user.id})\n"
        subscription_notes += f"Email abonné: {current_user.email}\n"
        
        # Extraire la section des informations du tiers depuis les notes du projet
        if "=== INFORMATIONS DU TIERS" in projet.notes:
            # Extraire uniquement la section des informations du tiers
            tier_section_start = projet.notes.find("=== INFORMATIONS DU TIERS")
            tier_section_end = projet.notes.find("=== FIN INFORMATIONS DU TIERS")
            if tier_section_end != -1:
                tier_section_end += len("=== FIN INFORMATIONS DU TIERS ===\n")
                tier_info_from_project = projet.notes[tier_section_start:tier_section_end]
            else:
                # Si pas de marqueur de fin, prendre jusqu'à la fin ou jusqu'à la prochaine section
                tier_info_from_project = projet.notes[tier_section_start:]
        else:
            # Si pas de section structurée, prendre toutes les notes
            tier_info_from_project = projet.notes
        
        subscription_notes += f"\n{tier_info_from_project}"
        logger.info(
            f"📝 Informations du tiers extraites depuis le projet de voyage (longueur: {len(tier_info_from_project)} caractères)"
        )
    
    # Vérifier aussi dans le questionnaire administratif si les informations du tiers y sont
    if request.administrative_form:
        personal_info = request.administrative_form.get("personal", {})
        # Si le questionnaire contient des informations qui indiquent que c'est pour un tiers
        # (par exemple, si le nom dans le questionnaire est différent de l'utilisateur connecté)
        if personal_info:
            tier_name = personal_info.get("fullName", "")
            if tier_name and tier_name != current_user.full_name:
                is_tier_subscription = True
                # Ajouter les informations du tiers dans les notes
                if not is_tier_subscription or "SOUSCRIPTION POUR UN TIERS" not in subscription_notes:
                    subscription_notes = f"{subscription_notes}\n\n⚠️ SOUSCRIPTION POUR UN TIERS ⚠️\n"
                    subscription_notes += f"Abonné (souscripteur): {current_user.full_name or current_user.username} (ID: {current_user.id})\n"
                    subscription_notes += f"Email abonné: {current_user.email}\n"
                
                tier_info_lines = [
                    f"\nInformations du tiers (bénéficiaire) depuis le questionnaire:",
                    f"Nom complet: {tier_name}",
                ]
                if personal_info.get("birthDate"):
                    tier_info_lines.append(f"Date de naissance: {personal_info.get('birthDate')}")
                if personal_info.get("passportNumber"):
                    tier_info_lines.append(f"Numéro de passeport: {personal_info.get('passportNumber')}")
                if personal_info.get("passportExpiryDate"):
                    tier_info_lines.append(f"Date d'expiration du passeport: {personal_info.get('passportExpiryDate')}")
                if personal_info.get("phone"):
                    tier_info_lines.append(f"Téléphone: {personal_info.get('phone')}")
                subscription_notes = f"{subscription_notes}\n" + "\n".join(tier_info_lines)

    # CRITIQUE: La souscription est TOUJOURS créée avec user_id de l'utilisateur connecté (abonné)
    # Les documents (attestations, cartes) utiliseront les informations du tiers depuis le questionnaire
    # mais la souscription elle-même reste liée à l'abonné pour la gestion du compte, paiements, etc.
    logger.info(
        f"Création de souscription - Abonné (user_id): {current_user.id} ({current_user.full_name or current_user.username}), "
        f"Pour un tiers: {is_tier_subscription}"
    )
    
    souscription = Souscription(
        user_id=current_user.id,  # TOUJOURS l'ID de l'utilisateur connecté (abonné)
        produit_assurance_id=produit.id,
        projet_voyage_id=projet.id,
        numero_souscription=numero_souscription,
        prix_applique=montant,
        prime_assurance=td.prime_assurance,
        frais_services=td.frais_services,
        date_debut=date_debut,
        date_fin=date_fin,
        statut=StatutSouscription.EN_ATTENTE,
        notes=subscription_notes
    )

    db.add(souscription)
    db.flush()

    questionnaire_administratif = _upsert_questionnaire(
        db,
        souscription.id,
        "administratif",
        request.administrative_form,
    )
    questionnaire_medical = _upsert_questionnaire(
        db,
        souscription.id,
        "medical",
        request.medical_form,
    )
    if questionnaire_medical and questionnaire_medical.reponses:
        med_rep = questionnaire_medical.reponses
        pm = None
        if isinstance(med_rep, dict):
            pm = med_rep.get("photoMedicale") or med_rep.get("photo_medicale")
        pm_len = len(pm) if isinstance(pm, str) else 0
        logger.info(
            "Checkout souscription_id=%s: photo médicale dans medical_form: %s (longueur chaîne=%s)",
            souscription.id,
            "oui" if pm_len else "non",
            pm_len,
        )
        AttestationService.persist_identity_photo_from_medical_answers(
            db,
            souscription.id,
            questionnaire_medical.reponses,
            uploaded_by_user_id=current_user.id,
        )

    _notify_questionnaire_reviewers(
        db=db,
        questionnaire=questionnaire_administratif,
        role=Role.TECHNICAL_REVIEWER,
        souscription=souscription,
        label="administratif / technique",
    )
    _notify_questionnaire_reviewers(
        db=db,
        questionnaire=questionnaire_medical,
        role=Role.MEDICAL_REVIEWER,
        souscription=souscription,
        label="médical",
    )

    paiement = Paiement(
        souscription_id=souscription.id,
        user_id=current_user.id,
        montant=montant,
        type_paiement=request.payment_method,
        statut=StatutPaiement.VALIDE,
        date_paiement=datetime.utcnow(),
        reference_transaction=f"TXN-{uuid.uuid4().hex[:16].upper()}"
    )

    db.add(paiement)
    db.commit()  # IMPORTANT: Commit pour s'assurer que le questionnaire est bien enregistré
    db.refresh(souscription)
    db.refresh(paiement)
    souscription.produit_assurance = produit
    souscription.projet_voyage = projet
    
    # Vérifier que le questionnaire administratif est bien enregistré avant de créer l'attestation
    if questionnaire_administratif:
        db.refresh(questionnaire_administratif)
        logger.info(
            f"✅ Questionnaire administratif vérifié - ID: {questionnaire_administratif.id}, "
            f"fullName dans reponses: '{questionnaire_administratif.reponses.get('personal', {}).get('fullName', 'NOT FOUND') if questionnaire_administratif.reponses else 'NO REPONSES'}'"
        )

    attestation = AttestationService.create_attestation_provisoire(
        db=db,
        souscription=souscription,
        paiement=paiement,
        user=current_user
    )

    # Déclencher l'analyse IA automatiquement en arrière-plan
    try:
        from app.services.ia_auto_service import IAAutoService
        from app.core.database import SessionLocal
        # Lancer en arrière-plan (non bloquant)
        import threading
        subscription_id = souscription.id  # Capturer l'ID avant le thread
        
        def run_ia_analysis():
            try:
                # Créer une nouvelle session pour le thread
                db_thread = SessionLocal()
                try:
                    # Recharger la souscription dans la nouvelle session
                    souscription_thread = db_thread.query(Souscription).filter(
                        Souscription.id == subscription_id
                    ).first()
                    if souscription_thread:
                        IAAutoService.trigger_ia_analysis(db=db_thread, souscription=souscription_thread, background=True)
                finally:
                    db_thread.close()
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse IA en arrière-plan: {e}", exc_info=True)
        
        thread = threading.Thread(target=run_ia_analysis)
        thread.daemon = True
        thread.start()
        logger.info(f"🔍 Analyse IA lancée en arrière-plan pour souscription {souscription.id}")
    except Exception as e:
        logger.warning(f"Impossible de lancer l'analyse IA automatique: {e}", exc_info=True)

    log_transaction(
        db=db,
        payment_id=paiement.id,
        action="checkout_completed",
        details={
            "subscription_id": souscription.id,
            "amount": float(montant),
            "payment_method": request.payment_method.value
        },
        user_id=current_user.id
    )

    return PaymentCheckoutResponse(
        subscription_id=souscription.id,
        numero_souscription=souscription.numero_souscription,
        payment_id=paiement.id,
        payment_status=paiement.statut,
        amount=montant,
        attestation_id=attestation.id,
        attestation_number=attestation.numero_attestation,
        attestation_url=attestation.url_signee
    )


@router.post("/confirm", response_model=PaymentConfirmResponse, status_code=status.HTTP_201_CREATED)
async def confirm_payment(
    request: PaymentConfirmRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirmer le paiement d'une souscription existante.
    Crée un paiement validé, active la souscription et génère une attestation provisoire.
    TOUTES les demandes sont automatiquement validées (pas de vrai processeur de paiement).
    """
    # Vérifier que la souscription existe et appartient à l'utilisateur
    logger.info(f"Tentative de confirmation de paiement pour souscription_id={request.souscription_id}, user_id={current_user.id}")
    
    souscription = db.query(Souscription).filter(
        and_(
            Souscription.id == request.souscription_id,
            Souscription.user_id == current_user.id
        )
    ).first()
    
    if not souscription:
        logger.warning(f"Souscription {request.souscription_id} non trouvée pour l'utilisateur {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    logger.info(f"Souscription trouvée: id={souscription.id}, statut={souscription.statut}, prix={souscription.prix_applique}")
    
    # Vérifier que la souscription n'est pas déjà payée
    if souscription.statut == StatutSouscription.ACTIVE:
        # Vérifier s'il existe déjà un paiement valide pour cette souscription
        existing_payment = db.query(Paiement).filter(
            and_(
                Paiement.souscription_id == request.souscription_id,
                Paiement.statut == StatutPaiement.VALIDE.name
            )
        ).first()
        
        if existing_payment:
            # Récupérer l'attestation associée
            from app.models.attestation import Attestation
            attestation = db.query(Attestation).filter(
                and_(
                    Attestation.souscription_id == request.souscription_id,
                    Attestation.paiement_id == existing_payment.id,
                    Attestation.type_attestation == "provisoire"
                )
            ).order_by(Attestation.created_at.desc()).first()
            
            logger.info(f"Paiement déjà effectué pour souscription {request.souscription_id}, retour du paiement existant")
            return PaymentConfirmResponse(
                payment_id=existing_payment.id,
                payment_status=existing_payment.statut.value,
                subscription_id=souscription.id,
                subscription_status=souscription.statut.value,
                amount=existing_payment.montant,
                attestation_id=attestation.id if attestation else None,
                attestation_number=attestation.numero_attestation if attestation else None,
                attestation_url=attestation.url_signee if attestation else None
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La souscription est déjà active mais aucun paiement valide trouvé"
            )
    
    # Vérifier que le montant correspond au prix de la souscription (tolérance de 0.01)
    if abs(float(request.montant) - float(souscription.prix_applique)) > 0.01:
        logger.warning(f"Montant incorrect: {request.montant} vs {souscription.prix_applique}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le montant ({request.montant}) ne correspond pas au prix de la souscription ({souscription.prix_applique})"
        )
    
    # Convertir la méthode de paiement en TypePaiement
    try:
        type_paiement = TypePaiement(request.methode_paiement)
    except ValueError:
        # Si la méthode n'est pas reconnue, utiliser CARTE_BANCAIRE par défaut
        logger.warning(f"Méthode de paiement non reconnue: {request.methode_paiement}, utilisation de CARTE_BANCAIRE")
        type_paiement = TypePaiement.CARTE_BANCAIRE
    
    # TRANSACTION ATOMIQUE : Tout doit réussir ou tout est annulé
    try:
        # Créer le paiement avec statut VALIDE (toutes les demandes sont validées)
        paiement = Paiement(
            souscription_id=request.souscription_id,
            user_id=current_user.id,
            montant=request.montant,
            type_paiement=type_paiement,
            statut=StatutPaiement.VALIDE,
            date_paiement=datetime.utcnow(),
            reference_transaction=f"TXN-{uuid.uuid4().hex[:16].upper()}"
        )
        
        db.add(paiement)
        db.flush()  # Pour obtenir l'ID du paiement
        
        # Mettre à jour le statut de la souscription
        souscription.statut = StatutSouscription.ACTIVE
        
        # Générer l'attestation provisoire (avec gestion d'erreur)
        try:
            attestation = AttestationService.create_attestation_provisoire(
                db=db,
                souscription=souscription,
                paiement=paiement,
                user=current_user
            )
            logger.info(f"Attestation provisoire créée: {attestation.numero_attestation}")
        except Exception as attestation_error:
            logger.error(f"Erreur lors de la génération de l'attestation: {attestation_error}")
            db.rollback()  # Annuler toute la transaction
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la génération de l'attestation provisoire: {str(attestation_error)}"
            )
        
        # Récupérer l'IP et le user agent
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")
        
        # Logger la transaction (ne pas faire échouer la transaction si le log échoue)
        try:
            log_transaction(
                db=db,
                payment_id=paiement.id,
                action="payment_confirmed",
                details={
                    "subscription_id": request.souscription_id,
                    "amount": float(request.montant),
                    "payment_method": request.methode_paiement,
                    "attestation_id": attestation.id,
                    "attestation_number": attestation.numero_attestation
                },
                user_id=current_user.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as log_error:
            logger.warning(f"Erreur lors du logging de la transaction (non bloquant): {log_error}")
        
        # COMMIT ATOMIQUE : Tout est validé en une seule fois
        db.commit()
        logger.info(f"Paiement confirmé avec succès: payment_id={paiement.id}, subscription_id={souscription.id}")
        
        # Rafraîchir les objets pour avoir les dernières données
        db.refresh(paiement)
        db.refresh(souscription)
        db.refresh(attestation)
        
        # Déclencher l'analyse IA automatiquement en arrière-plan
        try:
            from app.services.ia_auto_service import IAAutoService
            from app.core.database import SessionLocal
            import threading
            subscription_id = souscription.id
            
            def run_ia_analysis():
                try:
                    db_thread = SessionLocal()
                    try:
                        souscription_thread = db_thread.query(Souscription).filter(
                            Souscription.id == subscription_id
                        ).first()
                        if souscription_thread:
                            IAAutoService.trigger_ia_analysis(db=db_thread, souscription=souscription_thread, background=True)
                    finally:
                        db_thread.close()
                except Exception as e:
                    logger.error(f"Erreur lors de l'analyse IA en arrière-plan: {e}", exc_info=True)
            
            thread = threading.Thread(target=run_ia_analysis)
            thread.daemon = True
            thread.start()
            logger.info(f"🔍 Analyse IA lancée en arrière-plan pour souscription {souscription.id}")
        except Exception as e:
            logger.warning(f"Impossible de lancer l'analyse IA automatique: {e}", exc_info=True)
        
        return PaymentConfirmResponse(
            payment_id=paiement.id,
            payment_status=paiement.statut.value,
            subscription_id=souscription.id,
            subscription_status=souscription.statut.value,
            amount=paiement.montant,
            attestation_id=attestation.id,
            attestation_number=attestation.numero_attestation,
            attestation_url=attestation.url_signee
        )
        
    except HTTPException:
        # Ré-élever les HTTPException (erreurs de validation)
        raise
    except Exception as e:
        # En cas d'erreur inattendue, rollback et logger
        db.rollback()
        logger.error(f"Erreur lors de la confirmation du paiement: {e}")
        logger.exception(e)  # Log la trace complète
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la confirmation du paiement: {str(e)}"
        )


@router.get("/accounting/transactions", response_model=List[AccountingTransaction])
async def get_accounting_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fournir la trace des transactions financières pour les agents comptables."""
    require_accountant_role(current_user)

    assureur_scope = _get_assureur_scope_for_accountant(db, current_user)
    courtier_scope = _get_courtier_scope_for_accountant(db, current_user)
    if current_user.role == Role.AGENT_COMPTABLE_ASSUREUR:
        if not assureur_scope:
            return []
    if current_user.role == Role.AGENT_COMPTABLE_COURTIER:
        if not courtier_scope:
            return []

    payments = (
        db.query(Paiement)
        .options(
            joinedload(Paiement.souscription)
            .joinedload(Souscription.produit_assurance)
            .joinedload(ProduitAssurance.assureur_obj),
            joinedload(Paiement.souscription).joinedload(Souscription.user),
            joinedload(Paiement.user),
            joinedload(Paiement.attestations),
            joinedload(Paiement.refunds),
        )
        .order_by(Paiement.created_at.desc())
        .all()
    )

    results: List[AccountingTransaction] = []
    for payment in payments:
        montant_total = payment.montant or Decimal("0.00")

        subscription = payment.souscription
        if subscription:
            # Rafraîchir la souscription pour s'assurer d'avoir les données à jour
            db.refresh(subscription)
        
        produit = subscription.produit_assurance if subscription else None
        assureur_obj = produit.assureur_obj if produit else None
        assureur_id = produit.assureur_id if produit else None

        if assureur_scope is not None:
            if not assureur_id or assureur_id not in assureur_scope:
                continue

        # Comptable courtier : uniquement les paiements liés à une souscription dont le courtier_id
        # est explicitement l'un des courtiers dont il est l'agent (pas d'inférence par assureur).
        if courtier_scope is not None:
            sub_courtier_id = getattr(subscription, "courtier_id", None) if subscription else None
            if not sub_courtier_id or sub_courtier_id not in courtier_scope:
                continue

        final_decision = (subscription.validation_finale or "").lower() if subscription and subscription.validation_finale else "" if subscription and subscription.validation_finale else ""
        is_dossier_refused = final_decision == "rejected"
        
        # Vérifier si la souscription est résiliée
        is_resiliation = False
        if subscription:
            # Vérifier le statut de résiliation (priorité à cette vérification)
            demande_resiliation = subscription.demande_resiliation
            statut_souscription = subscription.statut
            
            logger.debug(f"Payment {payment.id}, Subscription {subscription.id}: demande_resiliation={demande_resiliation}, statut={statut_souscription}")
            
            if demande_resiliation == "approved":
                is_resiliation = True
                logger.info(f"Subscription {subscription.id} detected as resiliation (demande_resiliation=approved)")
            # Vérifier aussi si le statut de la souscription est RESILIEE
            elif statut_souscription == StatutSouscription.RESILIEE:
                is_resiliation = True
                logger.info(f"Subscription {subscription.id} detected as resiliation (statut=RESILIEE)")
            # Vérifier aussi si le paiement a un remboursement lié à une résiliation
            if not is_resiliation and payment.refunds:
                for refund in payment.refunds:
                    if refund.statut == "completed" and refund.souscription_id == subscription.id:
                        # Vérifier directement dans la DB
                        sub_check = db.query(Souscription).filter(
                            Souscription.id == subscription.id,
                            Souscription.demande_resiliation == "approved"
                        ).first()
                        if sub_check:
                            is_resiliation = True
                            logger.info(f"Subscription {subscription.id} detected as resiliation (via refund)")
                            break

        has_definitive_attestation = any(
            (att.type_attestation or "").lower() == "definitive"
            for att in (payment.attestations or [])
        )

        insured_share = Decimal("0.00")
        broker_share = Decimal("0.00")
        broker_id = getattr(subscription, "courtier_id", None) if subscription else None
        broker_name = None
        broker_pct = None
        if broker_id:
            courtier_row = db.query(Courtier).filter(Courtier.id == broker_id).first()
            if courtier_row:
                broker_name = courtier_row.nom

        # Règles de remboursement métier selon le motif.
        if is_resiliation:
            status_code = "refunded"
            status_label = "remboursé - résiliation"
            insured_share, mh_share = _refund_policy_breakdown(
                subscription, montant_total, "resiliation"
            )
            assureur_share = Decimal("0.00")
            broker_share = Decimal("0.00")
            logger.info(
                "Payment %s: remboursé - résiliation, assuré=%s, mh=%s",
                payment.id,
                insured_share,
                mh_share,
            )
        elif payment.statut == StatutPaiement.REMBOURSE or is_dossier_refused:
            status_code = "refunded"
            status_label = "remboursé - refus du dossier"
            insured_share, mh_share = _refund_policy_breakdown(
                subscription, montant_total, "refusal"
            )
            assureur_share = Decimal("0.00")
            broker_share = Decimal("0.00")
        elif has_definitive_attestation:
            status_code = "paid"
            status_label = "payé - attestation definitive"
            assureur_share, mh_share, broker_share, broker_id, broker_name, broker_pct = _ledger_with_optional_courtier(
                subscription, montant_total, db, assureur_id=assureur_id
            )
        else:
            status_code = "provisional"
            status_label = "reçu provisoire - attestation provisoire"
            assureur_share, mh_share, broker_share, broker_id, broker_name, broker_pct = _ledger_with_optional_courtier(
                subscription, montant_total, db, assureur_id=assureur_id
            )

        # Robustesse legacy: si l'écart comptable montre une commission courtier,
        # forcer le montant courtier et tenter de résoudre le nom/ID.
        # Ne jamais inférer un autre courtier que celui de la souscription si courtier_id est renseigné.
        explicit_sub_courtier_id = getattr(subscription, "courtier_id", None) if subscription else None
        if status_code in {"paid", "provisional"}:
            expected_broker = (montant_total - mh_share - assureur_share).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if expected_broker > Decimal("0.00") and (not broker_share or broker_share <= Decimal("0.00")):
                broker_share = expected_broker
            if expected_broker > Decimal("0.00") and (not broker_id or not broker_name) and assureur_id:
                if explicit_sub_courtier_id:
                    inferred = db.query(Courtier).filter(Courtier.id == explicit_sub_courtier_id).first()
                else:
                    inferred = (
                        db.query(Courtier)
                        .filter(Courtier.assureur_id == assureur_id)
                        .order_by(Courtier.id.asc())
                        .first()
                    )
                if inferred:
                    broker_id = inferred.id
                    broker_name = inferred.nom
                    if broker_pct is None:
                        broker_pct = Decimal(str(inferred.commission_pct or Decimal("0.00")))

        insured_user = payment.user
        assure_name = (
            (insured_user.full_name or "").strip()
            or (insured_user.username if insured_user else "")
            or (insured_user.email if insured_user else "")
            or "Assuré"
        )

        show_action = current_user.role in {
            Role.AGENT_COMPTABLE_MH,
            Role.FINANCE_MANAGER,
            Role.ADMIN,
        }
        action_label = None
        if show_action:
            if status_code == "refunded":
                action_label = "rembourser"
            else:
                action_label = _map_transaction_action(payment.statut)

        assureur_name = None
        if assureur_obj:
            assureur_name = assureur_obj.nom
        elif produit and produit.assureur:
            assureur_name = produit.assureur
        refund_courtier_name = None
        refund_courtier_id = getattr(subscription, "courtier_id", None) if subscription else None
        if not refund_courtier_id and assureur_id:
            fallback = (
                db.query(Courtier)
                .filter(Courtier.assureur_id == assureur_id)
                .order_by(Courtier.id.asc())
                .first()
            )
            if fallback:
                refund_courtier_id = fallback.id
                refund_courtier_name = fallback.nom
        elif refund_courtier_id:
            courtier_row = db.query(Courtier).filter(Courtier.id == refund_courtier_id).first()
            if courtier_row:
                refund_courtier_name = courtier_row.nom

        results.append(
            AccountingTransaction(
                payment_id=payment.id,
                subscription_id=payment.souscription_id,
                numero_souscription=subscription.numero_souscription if subscription else "—",
                assure=assure_name,
                montant_total=montant_total,
                montant_assureur=assureur_share,
                montant_courtier=broker_share or None,
                montant_mh=mh_share,
                montant_assure=insured_share or None,
                statut_transaction=status_label,
                status_code=status_code,
                action=action_label,
                reference_transaction=payment.reference_transaction,
                date_paiement=payment.date_paiement,
                produit_id=produit.id if produit else None,
                produit_nom=produit.nom if produit else None,
                assureur_id=assureur_id,
                assureur_nom=assureur_name,
                courtier_id=broker_id,
                courtier_nom=broker_name,
                commission_courtier_pct=broker_pct,
                commission_assureur_pct=None,
            )
        )

    # Créer un set des paiements déjà inclus pour éviter les doublons
    included_payment_ids = {result.payment_id for result in results}
    
    # Ajouter les remboursements de résiliation pour les paiements qui ne sont pas déjà dans la liste
    # (cas où le paiement n'existe pas ou n'a pas été chargé)
    refunds = (
        db.query(Refund)
        .join(Souscription, Refund.souscription_id == Souscription.id)
        .options(
            joinedload(Refund.souscription)
            .joinedload(Souscription.produit_assurance)
            .joinedload(ProduitAssurance.assureur_obj),
            joinedload(Refund.paiement).joinedload(Paiement.user),
        )
        .filter(Refund.statut == "completed")
        .filter(Souscription.demande_resiliation == "approved")
        .order_by(Refund.created_at.desc())
        .all()
    )

    for refund in refunds:
        # Ne pas ajouter si le paiement est déjà dans la liste
        if refund.paiement_id in included_payment_ids:
            continue
            
        subscription = refund.souscription
        if not subscription:
            continue

        if courtier_scope is not None:
            sub_courtier_id = getattr(subscription, "courtier_id", None)
            if not sub_courtier_id or sub_courtier_id not in courtier_scope:
                continue
        
        produit = subscription.produit_assurance if subscription else None
        assureur_obj = produit.assureur_obj if produit else None
        assureur_id = produit.assureur_id if produit else None

        if assureur_scope is not None:
            if not assureur_id or assureur_id not in assureur_scope:
                continue

        montant_remboursement = refund.montant or Decimal("0.00")
        montant_total_original = subscription.prix_applique or Decimal("0.00")

        if montant_remboursement > Decimal("0.00"):
            insured_share = montant_remboursement
            mh_share = (montant_total_original - insured_share).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            insured_share, mh_share = _refund_policy_breakdown(
                subscription, montant_total_original, "resiliation"
            )
        assureur_share = Decimal("0.00")
        broker_share = Decimal("0.00")

        insured_user = refund.paiement.user if refund.paiement else None
        assure_name = (
            (insured_user.full_name or "").strip()
            if insured_user
            else (subscription.user.full_name if subscription.user else "")
            or (subscription.user.username if subscription.user else "")
            or (subscription.user.email if subscription.user else "")
            or "Assuré"
        )

        assureur_name = None
        if assureur_obj:
            assureur_name = assureur_obj.nom
        elif produit and produit.assureur:
            assureur_name = produit.assureur

        rc_id = getattr(subscription, "courtier_id", None)
        rc_name = None
        rc_pct = None
        if rc_id:
            rc_row = db.query(Courtier).filter(Courtier.id == rc_id).first()
            if rc_row:
                rc_name = rc_row.nom
                rc_pct = Decimal(str(rc_row.commission_pct or Decimal("0.00")))

        results.append(
            AccountingTransaction(
                payment_id=refund.paiement_id if refund.paiement else 0,
                subscription_id=refund.souscription_id,
                numero_souscription=subscription.numero_souscription if subscription else "—",
                assure=assure_name,
                montant_total=montant_total_original,
                montant_assureur=assureur_share,
                montant_courtier=broker_share or None,
                montant_mh=mh_share,
                montant_assure=insured_share,
                statut_transaction="remboursé - résiliation",
                status_code="refunded",
                action=None,
                reference_transaction=refund.reference_remboursement,
                date_paiement=refund.date_remboursement or refund.created_at,
                produit_id=produit.id if produit else None,
                produit_nom=produit.nom if produit else None,
                assureur_id=assureur_id,
                assureur_nom=assureur_name,
                courtier_id=rc_id,
                courtier_nom=rc_name,
                commission_courtier_pct=rc_pct,
                commission_assureur_pct=None,
            )
        )

    return results

