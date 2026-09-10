"""Tests unitaires du moteur de décision automatique des souscriptions."""
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.enums import StatutSouscription
from app.services.subscription_decision_service import SubscriptionDecisionEngine


def _user(age: int | None = 35):
    birthdate = date(1990, 1, 1) if age is None else date(datetime.now().year - age, 1, 1)
    return SimpleNamespace(
        id=1,
        date_naissance=birthdate,
        full_name="Test User",
        email="test@example.com",
    )


def _product(
    age_min: int | None = 18,
    age_max: int | None = 69,
    duree_max: int | None = 365,
    zones: dict | None = None,
):
    return SimpleNamespace(
        id=1,
        age_minimum=age_min,
        age_maximum=age_max,
        duree_max_jours=duree_max,
        zones_geographiques=zones or {},
    )


def _project(destination: str = "France", days: int = 10, participants: int = 1):
    return SimpleNamespace(
        id=1,
        destination=destination,
        date_depart=datetime(2026, 10, 1),
        date_retour=datetime(2026, 10, 1) + __import__("datetime").timedelta(days=days),
        nombre_participants=participants,
    )


def _subscription():
    return SimpleNamespace(
        id=1,
        statut=StatutSouscription.EN_ATTENTE,
        prix_applique=Decimal("65000"),
        numero_souscription="S-001",
        validation_medicale=None,
        validation_technique=None,
        validation_finale=None,
    )


def _questionnaire(reponses: dict):
    return SimpleNamespace(reponses=reponses)


class TestSubscriptionDecisionEngineEvaluate:
    def test_approve_simple_dossier(self):
        sub = _subscription()
        result = SubscriptionDecisionEngine.evaluate(
            db=None,
            souscription=sub,
            user=_user(35),
            product=_product(),
            project=_project(),
            questionnaire=_questionnaire({}),
        )
        assert result.decision == "approve"
        assert sub.statut == StatutSouscription.EN_ATTENTE_PAIEMENT

    def test_reject_age_too_high(self):
        sub = _subscription()
        result = SubscriptionDecisionEngine.evaluate(
            db=None,
            souscription=sub,
            user=_user(95),
            product=_product(),
            project=_project(),
            questionnaire=_questionnaire({}),
        )
        assert result.decision == "reject"
        assert sub.statut == StatutSouscription.REFUSEE

    def test_reject_pregnancy_over_five_months(self):
        sub = _subscription()
        result = SubscriptionDecisionEngine.evaluate(
            db=None,
            souscription=sub,
            user=_user(30),
            product=_product(),
            project=_project(),
            questionnaire=_questionnaire({"enceinte": "oui", "mois_grossesse": 7}),
        )
        assert result.decision == "reject"
        assert sub.statut == StatutSouscription.REFUSEE

    def test_review_medical_pregnancy(self):
        sub = _subscription()
        result = SubscriptionDecisionEngine.evaluate(
            db=None,
            souscription=sub,
            user=_user(30),
            product=_product(),
            project=_project(),
            questionnaire=_questionnaire({"enceinte": "oui", "mois_grossesse": 3}),
        )
        assert result.decision == "review"
        assert result.primary_step == "medical"
        assert sub.statut == StatutSouscription.EN_ATTENTE_VALIDATION
        assert sub.validation_medicale == "pending"

    def test_review_medical_senior(self):
        sub = _subscription()
        result = SubscriptionDecisionEngine.evaluate(
            db=None,
            souscription=sub,
            user=_user(74),
            product=_product(age_max=80),
            project=_project(),
            questionnaire=_questionnaire({}),
        )
        assert result.decision == "review"
        assert result.primary_step == "medical"
        assert sub.validation_medicale == "pending"

    def test_review_technical_long_trip(self):
        sub = _subscription()
        result = SubscriptionDecisionEngine.evaluate(
            db=None,
            souscription=sub,
            user=_user(35),
            product=_product(),
            project=_project(days=45),
            questionnaire=_questionnaire({}),
        )
        assert result.decision == "review"
        assert "technical" in result.review_steps
        assert sub.validation_technique == "pending"

    def test_review_production_business_trip(self):
        sub = _subscription()
        result = SubscriptionDecisionEngine.evaluate(
            db=None,
            souscription=sub,
            user=_user(35),
            product=_product(),
            project=_project(),
            questionnaire=_questionnaire({"motif_voyage": "affaires"}),
        )
        assert result.decision == "review"
        assert "production" in result.review_steps


class TestSubscriptionDecisionEngineRecordReview:
    def test_medical_approved_then_technical_pending(self):
        sub = _subscription()
        sub.validation_medicale = "pending"
        sub.validation_technique = "pending"
        result = SubscriptionDecisionEngine.record_review(None, sub, "medical", True, 10)
        assert result.decision == "review"
        assert result.primary_step == "technical"
        assert sub.validation_medicale == "approved"
        assert sub.statut == StatutSouscription.EN_ATTENTE_VALIDATION

    def test_all_reviews_approved_ready_for_payment(self):
        sub = _subscription()
        sub.statut = StatutSouscription.EN_ATTENTE_VALIDATION
        sub.validation_medicale = "approved"
        sub.validation_technique = "pending"
        result = SubscriptionDecisionEngine.record_review(None, sub, "technical", True, 10)
        assert result.decision == "approve"
        assert sub.statut == StatutSouscription.EN_ATTENTE_PAIEMENT

    def test_medical_rejected_refuse_subscription(self):
        sub = _subscription()
        sub.statut = StatutSouscription.EN_ATTENTE_VALIDATION
        sub.validation_medicale = "pending"
        result = SubscriptionDecisionEngine.record_review(None, sub, "medical", False, 10, "grossesse risquée")
        assert result.decision == "reject"
        assert sub.statut == StatutSouscription.REFUSEE
        assert sub.validation_medicale == "rejected"
