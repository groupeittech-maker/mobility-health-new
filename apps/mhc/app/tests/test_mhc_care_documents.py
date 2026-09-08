"""Parcours documentaire MHC : numéros, workflow des bons, PDF."""
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import status

from app.core.mhc_nomenclature import (
    MhcOperationCode,
    format_attestation_number,
    format_avenant_annulation_number,
    format_bph_number,
    format_police_number,
    format_quittance_number,
    format_sinistre_number,
    parse_sinistre_order,
)
from app.core.mhc_tarif_reference import split_prime_nette
from app.core.enums import StatutSouscription
from app.models.alerte import Alerte
from app.models.souscription import Souscription
from app.models.sinistre import Sinistre
from app.services.mhc_care_document_pdf import build_care_document_pdf
from app.services.mhc_care_document_service import (
    CareDocumentPermissionError,
    allowed_next_actions,
    issue_care_document,
    validate_care_document,
)
from app.services.mhc_reference_service import allocate_police_number, allocate_sinistre_number


def _approve(db, sinistre, doc, *validators):
    """Fait approuver un document par une série de validateurs (double validation)."""
    for actor in validators:
        validate_care_document(db, sinistre, doc, actor, approve=True, alerte=sinistre.alerte)
    db.flush()

_SEQ = {"n": 0}


def _open_sinistre(db, test_user, test_product, test_hospital):
    _SEQ["n"] += 1
    seq = _SEQ["n"]
    product = test_product(db, code=f"MHC-DOC-PROD-{seq}", cout=Decimal("100.00"))
    subscription = Souscription(
        user_id=test_user.id,
        produit_assurance_id=product.id,
        numero_souscription=f"00{seq:04d}-10-011-001-2026",
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
        numero_alerte=f"ALT-MHC-DOC-{seq}",
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
        assert format_attestation_number(1) == "000001-101"
        assert format_avenant_annulation_number(92) == "000092-102"
        assert format_quittance_number(252) == "000252-119"
        assert MhcOperationCode.QUITTANCE_REGLEMENT.value == "119"
        assert MhcOperationCode.ARS.value == "121"

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
    def test_refuse_closes_dossier(
        self, db, test_user, test_product, test_hospital, test_doctor, test_medical_reviewer
    ):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        # BRPCU émis par le médecin-conseil, en attente de validation du pôle médical
        docs = issue_care_document(db, sinistre, "brpcu", test_doctor, notes="Hors garantie", alerte=alerte)
        db.flush()
        assert len(docs) == 1
        brpcu = docs[0]
        assert brpcu.document_type == "brpcu"
        assert "-112-" in brpcu.numero
        assert brpcu.validation_status == "en_attente"
        assert sinistre.statut != "annule"  # clôture différée à la validation
        # Validation par le pôle médical MHC → clôture (annulation)
        validate_care_document(db, sinistre, brpcu, test_medical_reviewer, approve=True, alerte=alerte)
        db.commit()
        assert brpcu.validation_status == "valide"
        assert sinistre.statut == "annule"
        assert allowed_next_actions(sinistre) == []

    def test_accept_then_hospital_then_exit(
        self, db, test_user, test_product, test_hospital, test_doctor, test_receptionist, test_medical_reviewer
    ):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        # BPCU (médecin-conseil) : sans validation → effectif immédiatement
        bpcu = issue_care_document(db, sinistre, "bpcu", test_doctor, payload={"motif_medical": "Fièvre"}, alerte=alerte)
        db.flush()
        assert bpcu[0].validation_status == "non_requise"
        assert bpcu[0].valid_until is not None
        assert "bh" in allowed_next_actions(sinistre)
        # BH émis par le partenaire-santé, double validation requise
        bh = issue_care_document(db, sinistre, "bh", test_receptionist, payload={"diagnostic": "Paludisme"}, alerte=alerte)
        db.flush()
        assert bh[0].validation_status == "en_attente"
        assert "-113" in bh[0].numero
        # tant que le BH n'est pas validé, pas d'enchaînement (hors décès)
        assert "bph" not in allowed_next_actions(sinistre)
        assert "bs" not in allowed_next_actions(sinistre)
        # double validation : médecin-conseil puis pôle médical MHC
        validate_care_document(db, sinistre, bh[0], test_doctor, approve=True, alerte=alerte)
        db.flush()
        assert bh[0].validation_status == "en_attente"  # un groupe encore manquant
        validate_care_document(db, sinistre, bh[0], test_medical_reviewer, approve=True, alerte=alerte)
        db.flush()
        assert bh[0].validation_status == "valide"
        assert "bph" in allowed_next_actions(sinistre)
        # BPH (partenaire-santé) + double validation
        bph = issue_care_document(db, sinistre, "bph", test_receptionist, payload={"motif_prolongation": "Surveillance"}, alerte=alerte)
        db.flush()
        assert "/" in bph[0].numero
        _approve(db, sinistre, bph[0], test_doctor, test_medical_reviewer)
        assert bph[0].validation_status == "valide"
        # Bulletin de sortie (partenaire-santé), guérison → clôture, sans validation
        bs = issue_care_document(
            db,
            sinistre,
            "bs",
            test_receptionist,
            payload={"mode_sortie": "guerison", "resume_rapport": "Amélioration"},
            alerte=alerte,
        )
        db.commit()
        assert len(bs) == 1
        assert bs[0].validation_status == "non_requise"
        assert sinistre.statut == "resolu"
        assert allowed_next_actions(sinistre) == []

    def test_exit_with_repatriation_is_simultaneous(
        self, db, test_user, test_product, test_hospital, test_doctor, test_receptionist, test_medical_reviewer
    ):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        issue_care_document(db, sinistre, "bpcu", test_doctor, alerte=alerte)
        db.flush()
        # BS (partenaire-santé) en mode rapatriement → BS + BRS simultanés
        created = issue_care_document(
            db,
            sinistre,
            "bs",
            test_receptionist,
            payload={"mode_sortie": "rapatriement_sanitaire", "destination": "Pointe-Noire"},
            alerte=alerte,
        )
        db.flush()
        types = [d.document_type for d in created]
        assert types == ["bs", "brs"]
        brs = created[1]
        assert created[0].validation_status == "non_requise"  # BS
        assert brs.validation_status == "en_attente"  # BRS : double validation
        assert sinistre.statut == "en_cours"
        assert "ars" not in allowed_next_actions(sinistre)  # BRS pas encore validé
        # double validation BRS : pôle médical MHC + partenaire-santé
        _approve(db, sinistre, brs, test_medical_reviewer, test_receptionist)
        assert brs.validation_status == "valide"
        assert "ars" in allowed_next_actions(sinistre)
        # ARS émise par le pôle médical MHC (sans validation) → clôture
        ars = issue_care_document(db, sinistre, "ars", test_medical_reviewer, payload={"bonne_reception": "oui"}, alerte=alerte)
        db.commit()
        assert ars[0].document_type == "ars"
        assert ars[0].validation_status == "non_requise"
        assert sinistre.statut == "resolu"

    def test_funeral_branch(
        self, db, test_user, test_product, test_hospital, test_doctor, test_medical_reviewer
    ):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        # BRF (médecin-conseil), validation par le pôle médical MHC
        brf = issue_care_document(db, sinistre, "brf", test_doctor, payload={"cause_deces": "AVC"}, alerte=alerte)
        db.flush()
        assert brf[0].document_type == "brf"
        assert brf[0].validation_status == "en_attente"
        assert allowed_next_actions(sinistre) == []  # BRF en attente
        validate_care_document(db, sinistre, brf[0], test_medical_reviewer, approve=True, alerte=alerte)
        db.flush()
        assert brf[0].validation_status == "valide"
        assert allowed_next_actions(sinistre) == ["arf"]
        # ARF émise par le pôle médical MHC (sans validation) → clôture
        arf = issue_care_document(db, sinistre, "arf", test_medical_reviewer, payload={"bonne_reception": "oui"}, alerte=alerte)
        db.commit()
        assert arf[0].document_type == "arf"
        assert sinistre.statut == "resolu"

    def test_invalid_transition(self, db, test_user, test_product, test_hospital, test_receptionist):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        try:
            # BH (partenaire-santé) sans BPCU → transition interdite
            issue_care_document(db, sinistre, "bh", test_receptionist, alerte=alerte)
            assert False, "BH sans BPCU devrait échouer"
        except ValueError:
            pass

    def test_emitter_role_enforced(
        self, db, test_user, test_product, test_hospital, test_doctor, test_receptionist
    ):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        # Un partenaire-santé ne peut pas émettre un BPCU (réservé médecin-conseil)
        try:
            issue_care_document(db, sinistre, "bpcu", test_receptionist, alerte=alerte)
            assert False, "BPCU par partenaire-santé devrait être refusé"
        except CareDocumentPermissionError:
            pass
        # Un médecin-conseil ne peut pas émettre un BH (réservé partenaire-santé)
        issue_care_document(db, sinistre, "bpcu", test_doctor, alerte=alerte)
        db.flush()
        try:
            issue_care_document(db, sinistre, "bh", test_doctor, alerte=alerte)
            assert False, "BH par médecin-conseil devrait être refusé"
        except CareDocumentPermissionError:
            pass

    def test_validation_wrong_role_and_refusal(
        self, db, test_user, test_product, test_hospital, test_doctor, test_receptionist, test_medical_reviewer
    ):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        issue_care_document(db, sinistre, "bpcu", test_doctor, alerte=alerte)
        db.flush()
        bh = issue_care_document(db, sinistre, "bh", test_receptionist, alerte=alerte)
        db.flush()
        # Le partenaire-santé n'est pas validateur du BH (médecin-conseil + pôle médical)
        try:
            validate_care_document(db, sinistre, bh[0], test_receptionist, approve=True, alerte=alerte)
            assert False, "Validation BH par partenaire-santé devrait être refusée"
        except CareDocumentPermissionError:
            pass
        # Refus par un validateur légitime → statut refuse, BH non effectif
        validate_care_document(db, sinistre, bh[0], test_medical_reviewer, approve=False, alerte=alerte)
        db.flush()
        assert bh[0].validation_status == "refuse"
        assert "bh" in allowed_next_actions(sinistre)  # ré-émission possible

    def test_pdf_generation(self, db, test_user, test_product, test_hospital, test_doctor):
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        docs = issue_care_document(db, sinistre, "bpcu", test_doctor, payload={"montant_max": "500000"}, alerte=alerte)
        pdf = build_care_document_pdf(docs[0])
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 500

    def test_bh_payload_enriched_from_hospital_stay(
        self, db, test_user, test_product, test_hospital, test_doctor, test_receptionist
    ):
        from datetime import datetime

        from app.models.hospital_stay import HospitalStay

        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        issue_care_document(db, sinistre, "bpcu", test_doctor, alerte=alerte)
        stay = HospitalStay(
            sinistre_id=sinistre.id,
            hospital_id=test_hospital.id,
            patient_id=test_user.id,
            assigned_doctor_id=test_doctor.id,
            service_concerne="Urgences",
            chambre="204",
            report_motif_consultation="Fièvre persistante",
            started_at=datetime.utcnow(),
            status="in_progress",
        )
        db.add(stay)
        db.flush()
        sinistre.hospital_stay = stay
        test_doctor.full_name = "Dr. Orientation Test"
        db.flush()

        # BH émis par le partenaire-santé, payload enrichi depuis le séjour
        bh = issue_care_document(
            db,
            sinistre,
            "bh",
            test_receptionist,
            payload={"admission_prevue": "2026-09-04T10:00"},
            alerte=alerte,
        )
        payload = bh[0].payload or {}
        assert payload.get("medecin_traitant") == "Dr. Orientation Test"
        assert payload.get("service") == "Urgences"
        assert payload.get("chambre") == "204"
        assert payload.get("motif_medical") == "Fièvre persistante"
        assert payload.get("admission_prevue") == "2026-09-04T10:00"

    def test_bpcu_brpcu_pdf_templates(self, db, test_user, test_product, test_hospital, test_doctor):
        """BPCU et BRPCU utilisent le gabarit officiel (sections numérotées, mentions légales)."""
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

    def test_emitter_403_and_validation_via_api(
        self,
        client,
        db,
        test_user,
        test_product,
        test_hospital,
        test_doctor,
        test_receptionist,
        test_medical_reviewer,
    ):
        from app.api.v1.auth import get_current_user
        from app.main import app

        sinistre, _, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        db.commit()
        base = f"/api/v1/mhc/sinistres/{sinistre.id}/care-documents"

        def _as(user):
            app.dependency_overrides[get_current_user] = lambda: user

        try:
            # Un partenaire-santé ne peut pas émettre un BPCU (réservé médecin-conseil) → 403
            _as(test_receptionist)
            r = client.post(base, json={"document_type": "bpcu"})
            assert r.status_code == status.HTTP_403_FORBIDDEN

            # Le médecin-conseil émet le BPCU (sans validation)
            _as(test_doctor)
            r = client.post(base, json={"document_type": "bpcu"})
            assert r.status_code == status.HTTP_201_CREATED
            assert r.json()[0]["validation_status"] == "non_requise"

            # Le partenaire-santé émet le BH (en attente de double validation)
            _as(test_receptionist)
            r = client.post(base, json={"document_type": "bh", "payload": {"diagnostic": "Paludisme"}})
            assert r.status_code == status.HTTP_201_CREATED
            bh = r.json()[0]
            assert bh["validation_status"] == "en_attente"
            bh_id = bh["id"]
            # Le partenaire-santé ne peut pas valider le BH → 403
            rv = client.post(f"/api/v1/mhc/care-documents/{bh_id}/validation", json={"approve": True})
            assert rv.status_code == status.HTTP_403_FORBIDDEN

            # Validation 1/2 : médecin-conseil
            _as(test_doctor)
            rv = client.post(f"/api/v1/mhc/care-documents/{bh_id}/validation", json={"approve": True})
            assert rv.status_code == status.HTTP_200_OK
            assert rv.json()["validation_status"] == "en_attente"

            # Validation 2/2 : pôle médical MHC → validé
            _as(test_medical_reviewer)
            rv = client.post(f"/api/v1/mhc/care-documents/{bh_id}/validation", json={"approve": True})
            assert rv.status_code == status.HTTP_200_OK
            assert rv.json()["validation_status"] == "valide"

            # Le BH validé débloque l'enchaînement
            _as(test_receptionist)
            listed = client.get(base)
            assert listed.status_code == status.HTTP_200_OK
            assert "bph" in listed.json()["actions_possibles"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)
