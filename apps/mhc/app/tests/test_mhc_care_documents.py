"""Parcours documentaire MHC : numéros, workflow des bons, PDF."""
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import status

from app.core.mhc_nomenclature import (
    format_bph_number,
    format_police_number,
    format_sinistre_number,
    parse_sinistre_order,
)
from app.core.mhc_tarif_reference import split_prime_nette
from app.core.enums import StatutSouscription
from app.models.alerte import Alerte
from app.models.souscription import Souscription
from app.models.sinistre import Sinistre
from app.services.mhc_care_document_pdf import build_care_document_pdf
from app.services.mhc_care_document_service import allowed_next_actions, issue_care_document
from app.services.mhc_reference_service import allocate_police_number, allocate_sinistre_number


def _open_sinistre(db, test_user, test_product, test_hospital):
    product = test_product(db, code="MHC-DOC-PROD", cout=Decimal("100.00"))
    subscription = Souscription(
        user_id=test_user.id,
        produit_assurance_id=product.id,
        numero_souscription="001001-10-011-001-2026",
        prix_applique=product.cout,
        date_debut=datetime.utcnow() - timedelta(days=1),
        date_fin=datetime.utcnow() + timedelta(days=29),
        statut=StatutSouscription.ACTIVE,
    )
    db.add(subscription)
    db.flush()
    alerte = Alerte(
        user_id=test_user.id,
        souscription_id=subscription.id,
        numero_alerte="ALT-MHC-DOC-1",
        latitude=Decimal("48.8566"),
        longitude=Decimal("2.3522"),
        description="Urgence test MHC",
        statut="en_cours",
        priorite="haute",
    )
    db.add(alerte)
    db.flush()
    sinistre = Sinistre(
        alerte_id=alerte.id,
        souscription_id=subscription.id,
        hospital_id=test_hospital.id,
        statut="en_cours",
    )
    db.add(sinistre)
    db.commit()
    db.refresh(sinistre)
    sinistre.souscription = subscription
    sinistre.hospital = test_hospital
    sinistre.alerte = alerte
    return sinistre, alerte, subscription


class TestMhcNomenclature:
    def test_police_and_sinistre_format(self):
        assert format_police_number(1300, 30, 52, 2026) == "001300-10-030-052-2026"
        assert format_sinistre_number(2500, 30, 52, 2026) == "002500-11-030-052-2026"
        assert format_bph_number(1350, 2, 2500) == "001350/02-002500-117"
        assert parse_sinistre_order("002500-11-030-052-2026") == 2500

    def test_repartition_20_pct(self):
        split = split_prime_nette(Decimal("6500"), Decimal("20"))
        assert split["part_assureur"] == Decimal("1300.00")
        assert split["part_scgre"] == Decimal("650.00")
        assert split["part_mhc"] == Decimal("4550.00")
        assert split["taxe"] == Decimal("975.00")
        assert split["prime_nette_totale"] == Decimal("7475.00")

    def test_allocate_counters(self, db, test_user, test_product, test_hospital):
        sinistre, _, subscription = _open_sinistre(db, test_user, test_product, test_hospital)
        n1 = allocate_sinistre_number(db, sinistre)
        n2 = allocate_sinistre_number(db, sinistre)
        assert n1 != n2
        assert "-11-" in n1
        police = allocate_police_number(db, subscription)
        assert "-10-" in police


class TestMhcCareDocumentWorkflow:
    def test_refuse_closes_dossier(self, db, test_user, test_product, test_hospital, test_doctor):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        docs = issue_care_document(db, sinistre, "brpcu", test_doctor, notes="Hors garantie", alerte=alerte)
        db.commit()
        assert len(docs) == 1
        assert docs[0].document_type == "brpcu"
        assert "-112-" in docs[0].numero
        assert sinistre.statut == "annule"
        assert allowed_next_actions(sinistre) == []

    def test_accept_then_hospital_then_exit(self, db, test_user, test_product, test_hospital, test_doctor):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        bpcu = issue_care_document(db, sinistre, "bpcu", test_doctor, payload={"motif_medical": "Fièvre"}, alerte=alerte)
        db.flush()
        assert bpcu[0].valid_until is not None
        assert "bh" in allowed_next_actions(sinistre)
        bh = issue_care_document(db, sinistre, "bh", test_doctor, payload={"diagnostic": "Paludisme"}, alerte=alerte)
        db.flush()
        assert bh[0].document_type == "bh"
        assert "-113" in bh[0].numero
        bph = issue_care_document(db, sinistre, "bph", test_doctor, payload={"motif_prolongation": "Surveillance"}, alerte=alerte)
        db.flush()
        assert "/" in bph[0].numero
        bs = issue_care_document(
            db,
            sinistre,
            "bs",
            test_doctor,
            payload={"mode_sortie": "guerison", "resume_rapport": "Amélioration"},
            alerte=alerte,
        )
        db.commit()
        assert len(bs) == 1
        assert sinistre.statut == "resolu"
        assert allowed_next_actions(sinistre) == []

    def test_exit_with_repatriation_is_simultaneous(self, db, test_user, test_product, test_hospital, test_doctor):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        issue_care_document(db, sinistre, "bpcu", test_doctor, alerte=alerte)
        created = issue_care_document(
            db,
            sinistre,
            "bs",
            test_doctor,
            payload={"mode_sortie": "rapatriement_sanitaire", "destination": "Pointe-Noire"},
            alerte=alerte,
        )
        db.commit()
        types = [d.document_type for d in created]
        assert types == ["bs", "brs"]
        assert sinistre.statut == "en_cours"
        assert "ars" in allowed_next_actions(sinistre)
        ars = issue_care_document(db, sinistre, "ars", test_doctor, payload={"bonne_reception": "oui"}, alerte=alerte)
        db.commit()
        assert ars[0].document_type == "ars"
        assert sinistre.statut == "resolu"

    def test_funeral_branch(self, db, test_user, test_product, test_hospital, test_doctor):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        brf = issue_care_document(db, sinistre, "brf", test_doctor, payload={"cause_deces": "AVC"}, alerte=alerte)
        db.flush()
        assert brf[0].document_type == "brf"
        assert allowed_next_actions(sinistre) == ["arf"]
        arf = issue_care_document(db, sinistre, "arf", test_doctor, payload={"bonne_reception": "oui"}, alerte=alerte)
        db.commit()
        assert arf[0].document_type == "arf"
        assert sinistre.statut == "resolu"

    def test_invalid_transition(self, db, test_user, test_product, test_hospital, test_doctor):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        try:
            issue_care_document(db, sinistre, "bh", test_doctor, alerte=alerte)
            assert False, "BH sans BPCU devrait échouer"
        except ValueError:
            pass

    def test_pdf_generation(self, db, test_user, test_product, test_hospital, test_doctor):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        docs = issue_care_document(db, sinistre, "bpcu", test_doctor, payload={"montant_max": "500000"}, alerte=alerte)
        pdf = build_care_document_pdf(docs[0])
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 500

    def test_bpcu_brpcu_pdf_templates(self, db, test_user, test_product, test_hospital, test_doctor):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        bpcu = issue_care_document(
            db,
            sinistre,
            "bpcu",
            test_doctor,
            payload={"motif_medical": "Traumatisme crânien", "montant_max": "750000", "devise": "XAF"},
            alerte=alerte,
        )
        bpcu_pdf = build_care_document_pdf(bpcu[0])
        assert bpcu_pdf[:4] == b"%PDF"
        assert len(bpcu_pdf) > 3000

        sinistre2, alerte2, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre2.numero_sinistre = allocate_sinistre_number(db, sinistre2)
        brpcu = issue_care_document(
            db,
            sinistre2,
            "brpcu",
            test_doctor,
            payload={"motif_refus": "Hors garanties contractuelles"},
            alerte=alerte2,
        )
        brpcu_pdf = build_care_document_pdf(brpcu[0])
        assert brpcu_pdf[:4] == b"%PDF"
        assert len(brpcu_pdf) > 3000
        assert bpcu_pdf != brpcu_pdf


class TestMhcCareDocumentApi:
    def test_referentiel_and_issue_via_api(
        self,
        client,
        db,
        test_user,
        test_product,
        test_hospital,
        test_doctor,
    ):
        from app.api.v1.auth import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: test_doctor
        try:
            sinistre, _, _ = _open_sinistre(db, test_user, test_product, test_hospital)
            sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
            db.commit()

            ref = client.get("/api/v1/mhc/referentiel")
            assert ref.status_code == status.HTTP_200_OK
            body = ref.json()
            assert any(d["type"] == "bpcu" for d in body["documents"])
            assert any(p["code"] == 30 for p in body["codes_pays"])

            created = client.post(
                f"/api/v1/mhc/sinistres/{sinistre.id}/care-documents",
                json={"document_type": "bpcu", "payload": {"motif_medical": "Traumatisme"}},
            )
            assert created.status_code == status.HTTP_201_CREATED
            data = created.json()
            assert data[0]["document_type"] == "bpcu"

            listed = client.get(f"/api/v1/mhc/sinistres/{sinistre.id}/care-documents")
            assert listed.status_code == status.HTTP_200_OK
            assert "bh" in listed.json()["actions_possibles"]

            pdf = client.get(f"/api/v1/mhc/care-documents/{data[0]['id']}/pdf")
            assert pdf.status_code == status.HTTP_200_OK
            assert pdf.headers["content-type"].startswith("application/pdf")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
