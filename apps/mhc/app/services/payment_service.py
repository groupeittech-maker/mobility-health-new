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
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.enums import StatutPaiement, StatutSouscription
from app.integrations.payment import get_payment_client
from app.integrations.payment.schemas import PaymentCustomer, PaymentIntentRequest
from app.models.finance_account import Account
from app.models.paiement import Paiement
from app.models.souscription import Souscription
from app.models.user import User
from app.services.attestation_service import AttestationService
from app.services.finance_service import FinanceService

logger = logging.getLogger(__name__)


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
        method: str = "mobile_money",
        callback_url: Optional[str] = None,
    ) -> tuple[Paiement, dict[str, Any]]:
        """Crée un Paiement MHC et un intent auprès de la plateforme de paiement africaine."""
        if subscription.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Souscription non autorisée",
            )

        if subscription.statut == StatutSouscription.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Souscription déjà payée",
            )

        client = get_payment_client()
        intent = client.create_intent(
            PaymentIntentRequest(
                amount=amount,
                currency="XAF",
                country=(user.pays_residence or "CI")[:2].upper(),
                reference=f"MHC-SUB-{subscription.id}",
                method=method,  # type: ignore[arg-type]
                customer=PaymentCustomer(
                    phone=user.telephone,
                    email=user.email,
                    name=user.full_name,
                ),
                callback_url=callback_url,
                metadata={"subscription_id": subscription.id, "user_id": user.id},
            )
        )

        payment = Paiement(
            souscription_id=subscription.id,
            user_id=user.id,
            montant=amount,
            type_paiement=payment_type,
            statut=StatutPaiement.EN_ATTENTE,
            reference_transaction=f"TXN-{uuid.uuid4().hex[:16].upper()}",
            reference_externe=intent.payment_id,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        return payment, {
            "payment_id": payment.id,
            "external_payment_id": intent.payment_id,
            "status": intent.status,
            "checkout_url": intent.checkout_url,
            "amount": float(amount),
            "currency": "XAF",
        }

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

            payment.statut = StatutPaiement.VALIDE
            payment.date_paiement = datetime.utcnow()
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
                            <p>Cordialement,<br>L'équipe Mobility Health</p>
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
                        L'équipe Mobility Health
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
                                f"Montant: {payment.montant} FCFA. Mobility Health"
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
