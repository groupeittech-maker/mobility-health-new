"""Tests unitaires — classification pipeline médecin référent (source de vérité web/mobile)."""
from types import SimpleNamespace

from app.services.referent_pipeline_service import (
    count_referent_pipeline_steps,
    get_referent_pipeline_step,
)


def _alerte(statut="en_cours"):
    return SimpleNamespace(statut=statut)


def _step(key, statut):
    return SimpleNamespace(step_key=key, statut=statut)


def _invoice(statut=None, validation_medicale=None):
    return SimpleNamespace(statut=statut, validation_medicale=validation_medicale)


def _stay(status, invoice=None):
    return SimpleNamespace(status=status, invoice=invoice)


def _sinistre(
    *,
    numero_sinistre=None,
    workflow_steps=None,
    hospital_stay=None,
):
    return SimpleNamespace(
        numero_sinistre=numero_sinistre,
        workflow_steps=workflow_steps or [],
        hospital_stay=hospital_stay,
    )


class TestGetReferentPipelineStep:
    def test_alerte_sans_sinistre_non_annulee(self):
        assert get_referent_pipeline_step(_alerte(), None) == "sinistre"

    def test_alerte_annulee_sans_sinistre(self):
        assert get_referent_pipeline_step(_alerte(statut="annulee"), None) == "resolu"

    def test_urgence_non_validee(self):
        sinistre = _sinistre(
            workflow_steps=[_step("verification_urgence", "pending")],
        )
        assert get_referent_pipeline_step(_alerte(), sinistre) == "sinistre"

    def test_sinistre_valide_apres_urgence(self):
        sinistre = _sinistre(
            numero_sinistre="SIN-001",
            workflow_steps=[_step("verification_urgence", "completed")],
        )
        assert get_referent_pipeline_step(_alerte(), sinistre) == "sinistre_valide"

    def test_rapport_a_valider(self):
        sinistre = _sinistre(
            workflow_steps=[_step("verification_urgence", "completed")],
            hospital_stay=_stay("awaiting_validation"),
        )
        assert get_referent_pipeline_step(_alerte(), sinistre) == "rapport"

    def test_rapport_valide(self):
        sinistre = _sinistre(
            workflow_steps=[_step("verification_urgence", "completed")],
            hospital_stay=_stay("validated"),
        )
        assert get_referent_pipeline_step(_alerte(), sinistre) == "rapport_valide"

    def test_facture_a_valider(self):
        sinistre = _sinistre(
            workflow_steps=[_step("verification_urgence", "completed")],
            hospital_stay=_stay("invoiced", _invoice(validation_medicale="pending")),
        )
        assert get_referent_pipeline_step(_alerte(), sinistre) == "facture"

    def test_facture_validee(self):
        sinistre = _sinistre(
            workflow_steps=[_step("verification_urgence", "completed")],
            hospital_stay=_stay("invoiced", _invoice(validation_medicale="approved")),
        )
        assert get_referent_pipeline_step(_alerte(), sinistre) == "facture_valide"

    def test_dossier_resolu_facture_payee(self):
        sinistre = _sinistre(
            workflow_steps=[_step("verification_urgence", "completed")],
            hospital_stay=_stay("invoiced", _invoice(statut="paid")),
        )
        assert get_referent_pipeline_step(_alerte(), sinistre) == "resolu"

    def test_dossier_resolu_facture_rejetee(self):
        sinistre = _sinistre(
            workflow_steps=[_step("verification_urgence", "completed")],
            hospital_stay=_stay("invoiced", _invoice(validation_medicale="rejected")),
        )
        assert get_referent_pipeline_step(_alerte(), sinistre) == "resolu"


class TestCountReferentPipelineSteps:
    def test_compte_par_etape(self):
        steps = ["sinistre", "sinistre", "sinistre_valide", "resolu", "resolu"]
        counts = count_referent_pipeline_steps(steps)
        assert counts["sinistre"] == 2
        assert counts["sinistre_valide"] == 1
        assert counts["resolu"] == 2
        assert counts["rapport"] == 0
