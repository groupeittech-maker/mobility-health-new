"""Workflow des avenants de police : suspension, réémission, PDF, rôles."""
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import status

from app.core.enums import StatutSouscription
from app.models.souscription import Souscription
from app.services.avenant_service import (
    build_avenant_pdf,
    decide_suspension,
    issue_reemission,
    request_suspension,
)

_SEQ = {"n": 0}


def _souscription(db, test_user, test_product):
    _SEQ["n"] += 1
    seq = _SEQ["n"]
    product = test_product(db, code=f"AVN-PROD-{seq}", cout=Decimal("100.00"))
    sous = Souscription(
        user_id=test_user.id,
        produit_assurance_id=product.id,
        numero_souscription=f"00{seq:04d}-10-011-001-2026",
        prix_applique=product.cout,
        date_debut=datetime.utcnow() - timedelta(days=1),
        date_fin=datetime.utcnow() + timedelta(days=29),
        statut=StatutSouscription.ACTIVE,
    )
    db.add(sous)
    db.commit()
    db.refresh(sous)
    return sous


class TestAvenantService:
    def test_suspension_request_then_validate_suspends_policy(
        self, db, test_user, test_product, test_agent_sinistre_assureur
    ):
        sous = _souscription(db, test_user, test_product)
        avenant = request_suspension(
            db, sous, test_user,
            motifs=["erreur_double_souscription"], pieces=["copie_police"],
        )
        db.commit()
        assert avenant.type_avenant == "suspension"
        assert avenant.statut == "demande"
        assert "-105" in avenant.numero
        # Tant que non validée, la police reste active
        assert sous.statut == StatutSouscription.ACTIVE
        # PDF généré
        assert build_avenant_pdf(db, avenant).read()[:4] == b"%PDF"

        decide_suspension(db, avenant, test_agent_sinistre_assureur, approve=True)
        db.commit()
        assert avenant.statut == "valide"
        assert avenant.decision_assureur == "approved"
        assert sous.statut == StatutSouscription.SUSPENDUE

    def test_suspension_refused_keeps_policy_active(
        self, db, test_user, test_product, test_agent_sinistre_assureur
    ):
        sous = _souscription(db, test_user, test_product)
        avenant = request_suspension(db, sous, test_user, motifs=["autre"], motif_autre="Test")
        db.commit()
        decide_suspension(db, avenant, test_agent_sinistre_assureur, approve=False)
        db.commit()
        assert avenant.statut == "refuse"
        assert sous.statut == StatutSouscription.ACTIVE

    def test_reemission_lifts_suspension(
        self, db, test_user, test_product, test_agent_sinistre_assureur
    ):
        sous = _souscription(db, test_user, test_product)
        avenant = request_suspension(db, sous, test_user, motifs=["changement_situation"])
        decide_suspension(db, avenant, test_agent_sinistre_assureur, approve=True)
        db.commit()
        assert sous.statut == StatutSouscription.SUSPENDUE

        reem = issue_reemission(db, sous, test_agent_sinistre_assureur)
        db.commit()
        assert reem.type_avenant == "reemission"
        assert "-106" in reem.numero
        assert reem.parent_avenant_id == avenant.id
        assert sous.statut == StatutSouscription.ACTIVE
        assert build_avenant_pdf(db, reem).read()[:4] == b"%PDF"

    def test_reemission_requires_suspended_policy(self, db, test_user, test_product, test_agent_sinistre_assureur):
        sous = _souscription(db, test_user, test_product)
        try:
            issue_reemission(db, sous, test_agent_sinistre_assureur)
            assert False, "réémission sans suspension devrait échouer"
        except ValueError:
            pass

    def test_autre_motif_requires_precision(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product)
        try:
            request_suspension(db, sous, test_user, motifs=["autre"], motif_autre="")
            assert False, "motif Autre sans précision devrait échouer"
        except ValueError:
            pass

    def test_unknown_motif_rejected(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product)
        try:
            request_suspension(db, sous, test_user, motifs=["motif_bidon"])
            assert False, "motif inconnu devrait échouer"
        except ValueError:
            pass


class TestAvenantApi:
    def test_full_flow_and_roles_via_api(
        self, client, db, test_user, test_product, test_agent_sinistre_assureur
    ):
        from app.api.v1.auth import get_current_user
        from app.main import app

        sous = _souscription(db, test_user, test_product)
        base = f"/api/v1/subscriptions/{sous.id}"

        def _as(user):
            app.dependency_overrides[get_current_user] = lambda: user

        try:
            # Le souscripteur demande la suspension
            _as(test_user)
            r = client.post(base + "/avenant-suspension", json={"motifs": ["erreur_double_souscription"], "pieces": ["copie_police"]})
            assert r.status_code == status.HTTP_201_CREATED, r.text
            avenant_id = r.json()["id"]
            assert r.json()["statut"] == "demande"

            # Le souscripteur ne peut pas valider (403)
            r = client.post(f"/api/v1/avenants/{avenant_id}/suspension-decision", json={"approve": True})
            assert r.status_code == status.HTTP_403_FORBIDDEN

            # L'assureur voit la demande dans la liste globale des suspensions en attente
            _as(test_agent_sinistre_assureur)
            r = client.get("/api/v1/avenants?type_avenant=suspension&statut=demande")
            assert r.status_code == status.HTTP_200_OK, r.text
            assert any(a["id"] == avenant_id for a in r.json())

            # L'assureur valide → police suspendue
            r = client.post(f"/api/v1/avenants/{avenant_id}/suspension-decision", json={"approve": True})
            assert r.status_code == status.HTTP_200_OK, r.text
            assert r.json()["statut"] == "valide"
            db.expire_all()
            assert db.query(Souscription).get(sous.id).statut == StatutSouscription.SUSPENDUE

            # Téléchargement du PDF de l'avenant
            r = client.get(f"/api/v1/avenants/{avenant_id}/download")
            assert r.status_code == status.HTTP_200_OK
            assert r.headers["content-type"].startswith("application/pdf")

            # Réémission → police active
            r = client.post(base + "/avenant-reemission", json={})
            assert r.status_code == status.HTTP_201_CREATED, r.text
            assert r.json()["type_avenant"] == "reemission"
            db.expire_all()
            assert db.query(Souscription).get(sous.id).statut == StatutSouscription.ACTIVE
        finally:
            app.dependency_overrides.pop(get_current_user, None)
