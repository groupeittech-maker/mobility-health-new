"""Service de paiement MHC — orchestre la souscription et la comptabilité.

Ce service est le point d'entrée pour toutes les opérations de paiement.
La logique comptable est déléguée à `FinanceService`.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.enums import StatutPaiement, StatutSouscription
from app.integrations.base import ExternalServiceError
from app.integrations.payment import get_payment_client
from app.integrations.payment.schemas import PaymentCustomer, PaymentIntentRequest
from app.models.finance_account import Account
from app.models.paiement import Paiement
from app.models.souscription import Souscription
from app.models.user import User
from app.services.attestation_service import AttestationService
from app.services.finance_service import FinanceService

logger = logging.getLogger(__name__)

# Correspondance type de paiement MHC → canal AfriPaie.
# Les moyens hors ligne (espèces, chèque, paiement différé) n'ont pas de canal :
# ils restent traités manuellement par les agents.
CHANNEL_BY_TYPE_PAIEMENT = {
    "carte_bancaire": "card",
    "mobile_money": "mobile_money",
    "mobile_money_airtel": "mobile_money",
    "mobile_money_mtn": "mobile_money",
    "mobile_money_orange": "mobile_money",
    "mobile_money_moov": "mobile_money",
    "virement": "bank_transfer",
    "prelevement": "bank_transfer",
}


def channel_for_payment_type(payment_type: str) -> Optional[str]:
    """Renvoie le canal AfriPaie pour un type de paiement MHC, ou None si hors ligne."""
    value = payment_type.value if hasattr(payment_type, "value") else str(payment_type)
    return CHANNEL_BY_TYPE_PAIEMENT.get(value)


def _country_code(value: Optional[str]) -> Optional[str]:
    """N'envoie à AfriPaie qu'un vrai code ISO-2 ; sinon on laisse l'indicatif
    téléphonique du client désigner le pays (routage automatique)."""
    if value and len(value.strip()) == 2 and value.strip().isalpha():
        return value.strip().upper()
    return None


def checkout_urls() -> tuple[Optional[str], Optional[str]]:
    """URLs de retour après la page de paiement hébergée AfriPaie."""
    base = (settings.FRONTEND_BASE_URL or "").rstrip("/")
    success = settings.PAYMENT_CHECKOUT_SUCCESS_URL or (
        f"{base}/payment-return.html?result=success" if base else None
    )
    cancel = settings.PAYMENT_CHECKOUT_CANCEL_URL or (
        f"{base}/payment-return.html?result=cancel" if base else None
    )
    return success, cancel


class PaymentService:
    """Facade paiement : souscription, orchestrateur externe, quittance."""

    @staticmethod
    def initiate_payment_intent(
        db: Session,
        user: User,
        subscription: Souscription,
        amount: Decimal,
        payment_type: str,
        *,
        flow: str = "direct",
        description: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        return_url: Optional[str] = None,
        callback_url: Optional[str] = None,
        allow_active: bool = False,
        before_commit: Optional[Callable[[Paiement], None]] = None,
    ) -> tuple[Paiement, dict[str, Any]]:
        """Crée un Paiement MHC et l'opération correspondante chez AfriPaie.

        `flow="checkout"` crée une session hébergée (redirection web) ;
        `flow="direct"` envoie un push USSD/OTP sur le téléphone du client.
        `allow_active=True` : complément de prime d'un avenant sur une police
        déjà active ; `before_commit` permet de rattacher le paiement créé.
        """
        if subscription.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Souscription non autorisée",
            )

        if subscription.statut == StatutSouscription.ACTIVE and not allow_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Souscription déjà payée",
            )

        channel = channel_for_payment_type(payment_type) or "mobile_money"

        # Le Paiement MHC est créé d'abord : son identifiant entre dans la
        # référence envoyée à AfriPaie (unicité en cas de nouvelle tentative).
        payment = Paiement(
            souscription_id=subscription.id,
            user_id=user.id,
            montant=amount,
            type_paiement=payment_type,
            statut=StatutPaiement.EN_ATTENTE,
            reference_transaction=f"TXN-{uuid.uuid4().hex[:16].upper()}",
        )
        db.add(payment)
        db.flush()
        if before_commit is not None:
            before_commit(payment)

        reference = f"MHC-SUB-{subscription.id}-P{payment.id}"
        default_success, default_cancel = checkout_urls()

        def _with_payment_param(url: Optional[str]) -> Optional[str]:
            """Ajoute payment_id à l'URL de retour : la page de retour MHC
            interroge ensuite GET /payments/{id}/status."""
            if not url:
                return url
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}payment_id={payment.id}"

        client = get_payment_client()
        try:
            intent = client.create_intent(
                PaymentIntentRequest(
                    amount=amount,
                    currency="XAF",
                    country=_country_code(getattr(user, "pays_residence", None)),
                    reference=reference,
                    method=channel,  # type: ignore[arg-type]
                    customer=PaymentCustomer(
                        phone=getattr(user, "telephone", None),
                        email=user.email,
                        name=user.full_name,
                    ),
                    description=description
                    or f"Souscription {subscription.numero_souscription or subscription.id}",
                    flow=flow,  # type: ignore[arg-type]
                    success_url=_with_payment_param(success_url or default_success),
                    cancel_url=_with_payment_param(cancel_url or default_cancel),
                    return_url=return_url,
                    callback_url=callback_url,
                    metadata={
                        "subscription_id": str(subscription.id),
                        "user_id": str(user.id),
                        "payment_id": str(payment.id),
                    },
                    idempotency_key=reference,
                )
            )
        except ExternalServiceError as exc:
            payment.statut = StatutPaiement.ECHOUE
            payment.notes = f"Erreur orchestrateur: {exc}"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Le service de paiement est indisponible. Réessayez plus tard.",
            ) from exc
        except ValueError as exc:
            payment.statut = StatutPaiement.ECHOUE
            payment.notes = str(exc)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        payment.reference_externe = intent.payment_id
        if intent.status == "processing":
            payment.statut = StatutPaiement.EN_COURS
        db.commit()
        db.refresh(payment)

        return payment, {
            "payment_id": payment.id,
            "external_payment_id": intent.payment_id,
            "status": intent.status,
            "provider": intent.provider,
            "checkout_url": intent.checkout_url,
            "action_type": intent.action_type,
            "instructions": intent.instructions,
            "expires_at": intent.expires_at,
            "amount": float(amount),
            "currency": "XAF",
        }

    @staticmethod
    def sync_external_status(db: Session, payment: Paiement) -> Optional[str]:
        """Interroge l'orchestrateur et met à jour le paiement MHC.

        Retourne le statut externe courant ("success", "processing", "failed",
        "expired"…) ou None si le paiement n'a pas de référence externe.
        """
        if not payment.reference_externe:
            return None

        client = get_payment_client()
        try:
            ext = client.get_status(payment.reference_externe)
        except ExternalServiceError as exc:
            logger.warning("Sync paiement %s impossible : %s", payment.id, exc)
            return None

        if ext.status == "success":
            if payment.statut != StatutPaiement.VALIDE:
                db.commit()
                PaymentService.process_payment_success(
                    payment_id=payment.id,
                    subscription_id=payment.souscription_id,
                    generate_attestation=True,
                )
            return "success"

        if ext.status in {"failed", "expired"}:
            if payment.statut in {StatutPaiement.EN_ATTENTE, StatutPaiement.EN_COURS}:
                payment.statut = StatutPaiement.ECHOUE
                if ext.failure_message:
                    payment.notes = f"{ext.failure_code or ext.status}: {ext.failure_message}"
                db.commit()
            return ext.status

        if ext.status == "processing" and payment.statut == StatutPaiement.EN_ATTENTE:
            payment.statut = StatutPaiement.EN_COURS
            db.commit()
        return ext.status

    @staticmethod
    def get_quittance(db: Session, payment: Paiement, user: User) -> Optional[dict[str, Any]]:
        """Extrait la quittance stockée dans `payment.notes` si elle existe."""
        if payment.user_id != user.id and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Non autorisé à consulter cette quittance",
            )
        if not payment.notes:
            return None
        try:
            payload = json.loads(payment.notes)
            if isinstance(payload, dict):
                return payload.get("quittance")
        except (json.JSONDecodeError, TypeError):
            return None
        return None

    @staticmethod
    def process_payment_success(
        payment_id: int,
        subscription_id: int,
        generate_attestation: bool = False,
    ) -> Optional[str]:
        """Traiter un paiement réussi avec transitions ACID.

        Cette méthode remplace l'ancienne fonction du routeur `payments.py`
        afin de séparer la couche service de l'API.
        """
        db = SessionLocal()
        try:
            payment = db.query(Paiement).filter(Paiement.id == payment_id).first()
            subscription = db.query(Souscription).filter(Souscription.id == subscription_id).first()

            if not payment or not subscription:
                raise ValueError("Payment or subscription not found")

            from app.services.avenant_service import avenant_for_payment, finalize_avenant_payment

            avenant = avenant_for_payment(db, payment.id)
            payment.statut = StatutPaiement.VALIDE
            payment.date_paiement = datetime.utcnow()
            if avenant is None:
                subscription.statut = StatutSouscription.ACTIVE

            # Encaissement du montant sur le compte principal (paiement collecté).
            # La répartition entre assureur, courtier, MH est gérée séparément par FinanceService.
            enc_account = (
                db.query(Account)
                .filter(Account.account_number == "ENC-XAF")
                .first()
            )
            if not enc_account:
                enc_account = Account(
                    account_number="ENC-XAF",
                    account_name="Encaissement principal",
                    account_type="internal",
                    currency="XAF",
                    balance=Decimal("0.00"),
                )
                db.add(enc_account)
                db.flush()

            FinanceService.create_movement(
                db=db,
                account_id=enc_account.id,
                movement_type="payment",
                amount=payment.montant,
                description=f"Encaissement souscription {subscription.numero_souscription}",
                reference=f"PAY-{payment.reference_transaction}",
                reference_type="payment",
                related_id=payment.id,
                currency="XAF",
            )

            # Complément de prime d'un avenant (modification / prorogation) :
            # application de l'avenant + quittance 119, pas de nouvelle souscription.
            if avenant is not None:
                finalize_avenant_payment(db, avenant, payment)
                PaymentService.log_transaction(
                    db=db,
                    payment_id=payment_id,
                    action="avenant_payment_success",
                    details={"subscription_id": subscription_id, "avenant_id": avenant.id, "amount": float(payment.montant)},
                    user_id=payment.user_id,
                )
                db.commit()
                return avenant.numero

            attestation_number = None
            attestation_url = None

            if generate_attestation:
                user = db.query(User).filter(User.id == payment.user_id).first()
                if user:
                    try:
                        attestation = AttestationService.create_attestation_definitive(
                            db=db,
                            souscription=subscription,
                            paiement=payment,
                            user=user,
                        )
                        attestation_number = attestation.numero_attestation
                        attestation_url = attestation.url_signee
                    except Exception as attestation_error:
                        logger.warning(
                            "Attestation définitive non générée pour le paiement %s: %s",
                            payment.id,
                            attestation_error,
                        )
                    try:
                        AttestationService.issue_quittance_paiement(db, subscription, payment, user)
                    except Exception as quittance_error:
                        logger.warning(
                            "Quittance non générée pour le paiement %s: %s",
                            payment.id,
                            quittance_error,
                        )
                else:
                    attestation_number = f"ATT-{subscription.numero_souscription}-{datetime.utcnow().strftime('%Y%m%d')}"

            PaymentService.log_transaction(
                db=db,
                payment_id=payment_id,
                action="payment_success",
                details={
                    "subscription_id": subscription_id,
                    "attestation_number": attestation_number,
                    "amount": float(payment.montant),
                },
                user_id=payment.user_id,
            )

            db.commit()
            logger.info("Payment %s processed. Attestation: %s", payment_id, attestation_number)

            if generate_attestation and attestation_number:
                try:
                    from app.workers.tasks import send_email, send_sms

                    user = db.query(User).filter(User.id == payment.user_id).first()
                    if user:
                        display_name = user.full_name or user.username
                        email_subject = f"Attestation d'assurance - {attestation_number}"
                        email_body_html = f"""
                        <html>
                        <body>
                            <h2>Votre attestation d'assurance est prête</h2>
                            <p>Bonjour {display_name},</p>
                            <p>Votre paiement a été validé avec succès. Votre attestation définitive et votre quittance sont disponibles.</p>
                            <p><strong>Numéro d'attestation:</strong> {attestation_number}</p>
                            <p><strong>Numéro de souscription:</strong> {subscription.numero_souscription}</p>
                            <p><strong>Montant payé:</strong> {payment.montant} FCFA</p>
                            {f'<p><a href="{attestation_url}">Télécharger votre attestation</a></p>' if attestation_url else ''}
                            <p>Cordialement,<br>L'équipe Mobility Health Care</p>
                        </body>
                        </html>
                        """
                        email_body_text = f"""
                        Votre attestation d'assurance est prête

                        Bonjour {display_name},

                        Votre paiement a été validé avec succès. Votre attestation définitive et votre quittance sont disponibles.

                        Numéro d'attestation: {attestation_number}
                        Numéro de souscription: {subscription.numero_souscription}
                        Montant payé: {payment.montant} FCFA

                        {f'Télécharger votre attestation: {attestation_url}' if attestation_url else ''}

                        Cordialement,
                        L'équipe Mobility Health Care
                        """
                        if user.email:
                            send_email.delay(
                                to_email=user.email,
                                subject=email_subject,
                                body_html=email_body_html,
                                body_text=email_body_text,
                                user_id=user.id,
                            )
                        if user.telephone:
                            sms_message = (
                                f"Votre attestation {attestation_number} est prête. "
                                f"Montant: {payment.montant} FCFA. Mobility Health Care"
                            )
                            send_sms.delay(
                                to_phone=user.telephone,
                                message=sms_message,
                                user_id=user.id,
                            )
                except Exception as e:
                    logger.error("Error queuing email/SMS for attestation: %s", e)

            return attestation_number

        except Exception as e:
            db.rollback()
            logger.error("Error processing payment %s: %s", payment_id, e)
            raise
        finally:
            db.close()

    @staticmethod
    def log_transaction(
        db: Session,
        payment_id: int,
        action: str,
        details: dict,
        user_id: Optional[int] = None,
    ):
        """Logger une transaction de paiement."""
        try:
            from app.models.transaction_log import TransactionLog

            log_entry = TransactionLog(
                payment_id=payment_id,
                user_id=user_id,
                action=action,
                details=details,
            )
            db.add(log_entry)
            db.commit()
            logger.info("Transaction logged: payment_id=%s, action=%s", payment_id, action)
        except Exception as e:
            db.rollback()
            logger.error("Error logging transaction: %s", e)
