"""Actions sur une police (workflow MyMHC V3) : annulation 102, modification 107,
prorogation 108, règle exclusive, ristourne / quittance 120."""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import status

from app.core.enums import Role, StatutPaiement, StatutSouscription, TypePaiement
from app.core.security import get_password_hash
from app.models.avenant import Avenant
from app.models.paiement import Paiement
from app.models.ristourne import Ristourne
from app.models.souscription import Souscription
from app.models.user import User
from app.services import avenant_service
from app.services.avenant_service import AvenantError

_SEQ = {"n": 0}
TODAY = datetime.utcnow().date()


@pytest.fixture(autouse=True)
def _no_side_effects(monkeypatch):
    """Notifications (session dédiée) et régénération d'attestation (MinIO) neutralisées."""
    from app.services.attestation_service import AttestationService
    from app.services.notification_service import NotificationService

    calls = {"attestations": 0}

    def _fake_attestation(**kwargs):
        calls["attestations"] += 1
        return None

    monkeypatch.setattr(NotificationService, "create_notification", staticmethod(lambda **kw: None))
    monkeypatch.setattr(AttestationService, "create_attestation_definitive", staticmethod(_fake_attestation))
    return calls


def _dt(days: int) -> datetime:
    return datetime.combine(TODAY + timedelta(days=days), datetime.min.time())


def _souscription(db, user, test_product, *, start=10, end=20, statut=StatutSouscription.ACTIVE, paid=True):
    _SEQ["n"] += 1
    seq = _SEQ["n"]
    product = test_product(db, code=f"AVN-PROD-{seq}", cout=Decimal("13000"))
    sous = Souscription(
        user_id=user.id,
        produit_assurance_id=product.id,
        numero_souscription=f"{seq:06d}-10-011-001-2026",
        prix_applique=Decimal("13000"),
        prime_assurance=Decimal("10000"),
        cout_police=Decimal("1000"),
        frais_services=Decimal("1000"),
        taxes_total=Decimal("1000"),
        date_debut=_dt(start),
        date_fin=_dt(end),
        statut=statut,
    )
    db.add(sous)
    db.flush()
    if paid:
        db.add(Paiement(
            souscription_id=sous.id,
            user_id=user.id,
            montant=Decimal("13000"),
            type_paiement=TypePaiement.MOBILE_MONEY_MTN,
            statut=StatutPaiement.VALIDE,
            date_paiement=datetime.utcnow(),
            reference_transaction=f"TXN-AVN-{seq}",
        ))
    db.commit()
    db.refresh(sous)
    return sous


def _actions(db, sous, today=TODAY):
    return {k: v["disponible"] for k, v in avenant_service.available_actions(db, sous, today)["actions"].items()}


class TestAnnulation:
    def test_simulation_does_not_change_policy(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product)
        result = avenant_service.request_annulation(db, sous, test_user, confirm=False)
        assert result.simulation
        # Prime + taxes remboursées ; coût de police et frais de service retenus.
        assert result.montants.total == Decimal("11000")
        assert sous.statut == StatutSouscription.ACTIVE

    def test_confirmed_annulation_emits_102_and_ristourne(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product)
        result = avenant_service.request_annulation(db, sous, test_user, confirm=True, motif="Voyage annulé")
        db.commit()
        assert sous.statut == StatutSouscription.RESILIEE
        assert result.avenant.numero.endswith("-102")
        assert result.avenant.statut == "emis"
        assert result.ristourne.statut == "a_rembourser"
        assert result.ristourne.montant_total == Decimal("11000")
        assert result.ristourne.numero is None
        assert avenant_service.build_avenant_pdf(db, result.avenant).read()[:4] == b"%PDF"
        # Police annulée : plus aucune action possible.
        assert not any(_actions(db, sous).values())

    def test_unpaid_dossier_cancelled_without_document(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product, statut=StatutSouscription.EN_ATTENTE_VALIDATION, paid=False)
        result = avenant_service.request_annulation(db, sous, test_user, confirm=True)
        assert sous.statut == StatutSouscription.RESILIEE
        assert result.avenant is None and result.ristourne is None

    def test_annulation_refused_on_or_after_start_date(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product, start=0, end=10)
        with pytest.raises(AvenantError):
            avenant_service.request_annulation(db, sous, test_user, confirm=True)


def _countries(db, monkeypatch, zones=None):
    """Trois pays de destination : FR et BE en EXTRA_AFRIQUE, SN en INTRA_AFRIQUE."""
    from app.models.destination import DestinationCountry

    rows = {}
    for code, nom in (("FR", "France"), ("BE", "Belgique"), ("SN", "Sénégal")):
        country = db.query(DestinationCountry).filter(DestinationCountry.code == code).first()
        if country is None:
            country = DestinationCountry(code=code, nom=nom, est_actif=True)
            db.add(country)
            db.flush()
        rows[code] = country
    zones = zones or {"FR": "EXTRA_AFRIQUE", "BE": "EXTRA_AFRIQUE", "SN": "INTRA_AFRIQUE"}
    by_id = {rows[c].id: z for c, z in zones.items()}
    monkeypatch.setattr(avenant_service, "_tariff_zone", lambda db, sous, cid: by_id.get(cid))
    db.commit()
    return rows


def _with_destination(db, sous, country):
    from app.models.projet_voyage import ProjetVoyage

    projet = ProjetVoyage(
        user_id=sous.user_id, titre="Voyage", destination=country.nom, destination_country_id=country.id,
        date_depart=sous.date_debut, date_retour=sous.date_fin,
    )
    db.add(projet)
    db.flush()
    sous.projet_voyage_id = projet.id
    db.commit()
    db.refresh(sous)
    return projet


class TestModification:
    """Règle du PDF (§6) : destination dans la même zone tarifaire, dates inchangées, sans ajustement."""

    def test_same_zone_destination_emits_107_without_adjustment(self, db, test_user, test_product, monkeypatch, _no_side_effects):
        countries = _countries(db, monkeypatch)
        sous = _souscription(db, test_user, test_product, start=-3, end=10)  # pendant le séjour
        _with_destination(db, sous, countries["FR"])
        debut, fin, prix = sous.date_debut, sous.date_fin, sous.prix_applique

        simulation = avenant_service.request_modification(
            db, sous, test_user, destination_country_id=countries["BE"].id, confirm=False,
        )
        assert simulation.simulation and simulation.montants.total == 0
        assert simulation.payment_info["nouvelle_destination"] == "Belgique"

        result = avenant_service.request_modification(
            db, sous, test_user, destination_country_id=countries["BE"].id, destination_ville="Bruxelles", confirm=True,
        )
        db.commit()
        db.refresh(sous)
        avenant = result.avenant
        assert avenant.statut == "emis" and avenant.numero.endswith("-107")
        assert avenant.nature_ajustement == "aucun" and avenant.montant_ajustement == 0
        assert (sous.date_debut, sous.date_fin, sous.prix_applique) == (debut, fin, prix)
        assert sous.projet_voyage.destination_country_id == countries["BE"].id
        assert sous.projet_voyage.destination == "Bruxelles"
        assert avenant.payload["ancienne_destination"] == "France"
        assert _no_side_effects["attestations"] == 1
        assert avenant_service.build_avenant_pdf(db, avenant).read()[:4] == b"%PDF"
        # Avenant émis immédiatement : aucune demande en cours, les actions restent disponibles.
        assert _actions(db, sous)["prorogation"] is True

    def test_other_tariff_zone_refused(self, db, test_user, test_product, monkeypatch):
        countries = _countries(db, monkeypatch)
        sous = _souscription(db, test_user, test_product)
        _with_destination(db, sous, countries["FR"])
        with pytest.raises(AvenantError, match="même zone tarifaire"):
            avenant_service.request_modification(db, sous, test_user, destination_country_id=countries["SN"].id, confirm=False)

    def test_identical_destination_refused(self, db, test_user, test_product, monkeypatch):
        countries = _countries(db, monkeypatch)
        sous = _souscription(db, test_user, test_product)
        _with_destination(db, sous, countries["FR"])
        with pytest.raises(AvenantError, match="identique"):
            avenant_service.request_modification(db, sous, test_user, destination_country_id=countries["FR"].id, confirm=False)

    def test_modification_refused_after_expiry(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product, start=-20, end=-1)
        assert _actions(db, sous)["modification"] is False

    def test_modification_available_during_stay(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product, start=-2, end=8)
        assert _actions(db, sous) == {"annulation": False, "modification": True, "prorogation": True}


class TestProrogation:
    def test_prorogation_prorata_and_payment_emits_108(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product, start=-2, end=8)
        result = avenant_service.request_prorogation(
            db, sous, test_user, nouvelle_date_fin=TODAY + timedelta(days=13), confirm=True,
        )
        db.commit()
        assert result.avenant.montant_ajustement == Decimal("6000")  # 12000 × 5/10
        avenant_service.start_avenant_payment(db, result.avenant, test_user, payment_type="mobile_money_mtn")
        db.commit()
        db.refresh(sous)
        assert result.avenant.numero.endswith("-108")
        assert sous.date_fin.date() == TODAY + timedelta(days=13)
        assert avenant_service.build_avenant_pdf(db, result.avenant).read()[:4] == b"%PDF"

    def test_prorogation_limited_to_92_days(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product, start=-2, end=8)
        with pytest.raises(AvenantError):
            avenant_service.request_prorogation(
                db, sous, test_user, nouvelle_date_fin=TODAY + timedelta(days=91), confirm=False,
            )

    def test_prorogation_after_initial_end_refused(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product, start=-20, end=-1)
        with pytest.raises(AvenantError):
            avenant_service.request_prorogation(
                db, sous, test_user, nouvelle_date_fin=TODAY + timedelta(days=5), confirm=False,
            )

    def test_abandon_and_stale_expiry_reactivate_actions(self, db, test_user, test_product):
        sous = _souscription(db, test_user, test_product)
        first = avenant_service.request_prorogation(
            db, sous, test_user, nouvelle_date_fin=TODAY + timedelta(days=25), confirm=True,
        ).avenant
        avenant_service.abandon_pending(db, first)
        db.commit()
        assert all(_actions(db, sous).values())

        second = avenant_service.request_prorogation(
            db, sous, test_user, nouvelle_date_fin=TODAY + timedelta(days=25), confirm=True,
        ).avenant
        db.commit()
        assert avenant_service.expire_stale_pending(db, today=TODAY + timedelta(days=21)) == 1
        assert second.statut == "abandonne"


class TestPolicyActionsApi:
    def test_full_flow_via_api(self, client, db, test_user, test_product, test_admin):
        from app.api.v1.auth import get_current_user
        from app.main import app

        sous = _souscription(db, test_user, test_product)
        other = User(
            email="other@example.com", username="other", hashed_password=get_password_hash("x"),
            full_name="Other", role=Role.USER, is_active=True,
        )
        db.add(other)
        db.commit()
        base = f"/api/v1/subscriptions/{sous.id}"

        def _as(user):
            app.dependency_overrides[get_current_user] = lambda: user

        try:
            _as(other)
            r = client.post(base + "/actions/annulation", json={"confirmer": True})
            assert r.status_code == status.HTTP_403_FORBIDDEN

            _as(test_user)
            r = client.get(base + "/actions")
            assert r.status_code == 200, r.text
            assert r.json()["actions"]["modification"]["disponible"] is True
            assert r.json()["duree_max_jours"] == 92

            body = {"nouvelle_date_fin": str(TODAY + timedelta(days=30))}
            r = client.post(base + "/actions/prorogation", json=body)
            assert r.status_code == 200, r.text
            assert r.json()["simulation"] is True
            assert Decimal(r.json()["montants"]["total"]) == Decimal("12000")
            assert db.query(Avenant).count() == 0

            r = client.post(base + "/actions/prorogation", json={**body, "confirmer": True})
            assert r.status_code == 200, r.text
            avenant_id = r.json()["avenant"]["id"]

            r = client.get(base + "/actions")
            assert r.json()["action_en_cours"]["id"] == avenant_id
            assert r.json()["actions"]["annulation"]["disponible"] is False
            assert r.json()["actions"]["modification"]["disponible"] is False
            r = client.post(base + "/actions/annulation", json={"confirmer": True})
            assert r.status_code == 400

            r = client.post(f"/api/v1/avenants/{avenant_id}/payer", json={"payment_type": "mobile_money_mtn"})
            assert r.status_code == 200, r.text
            assert r.json()["avenant"]["statut"] == "emis"
            r = client.get(f"/api/v1/avenants/{avenant_id}/download")
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("application/pdf")

            r = client.post(base + "/actions/annulation", json={"confirmer": True})
            assert r.status_code == 200, r.text
            ristourne_id = r.json()["ristourne"]["id"]
            assert Decimal(r.json()["ristourne"]["montant_total"]) == Decimal("22000")

            r = client.post(f"/api/v1/ristournes/{ristourne_id}/confirmer", json={"moyen_remboursement": "virement"})
            assert r.status_code == status.HTTP_403_FORBIDDEN

            _as(test_admin)
            r = client.get("/api/v1/ristournes?statut=a_rembourser")
            assert [x["id"] for x in r.json()] == [ristourne_id]
            r = client.post(f"/api/v1/ristournes/{ristourne_id}/confirmer", json={"moyen_remboursement": "virement"})
            assert r.status_code == 200, r.text
            assert r.json()["numero"].endswith("-120")

            _as(test_user)
            r = client.get(f"/api/v1/ristournes/{ristourne_id}/download")
            assert r.status_code == 200
            assert db.query(Ristourne).count() == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)
