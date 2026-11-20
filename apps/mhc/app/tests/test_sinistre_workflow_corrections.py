"""Corrections du workflow sinistre : décision médecin-conseil, bons expirés,
déclaration manuelle et chaîne de facturation (médecin-conseil → affaires
médicales → paiement MHC)."""
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import status

from app.core.enums import Role, StatutSouscription
from app.core.security import get_password_hash
from app.models.alerte import Alerte
from app.models.hospital_stay import HospitalStay
from app.models.invoice import Invoice, InvoiceStatus
from app.models.mhc_care_document import MhcCareDocument
from app.models.sinistre import Sinistre
from app.models.souscription import Souscription
from app.models.user import User
from app.services.mhc_care_document_service import (
    allowed_next_actions,
    issue_care_document,
    issue_decision_documents,
)
from app.services.mhc_reference_service import allocate_sinistre_number

_SEQ = {"n": 0}


def _make_user(db, role, suffix):
    user = User(
        email=f"{suffix}@example.com",
        username=suffix,
        hashed_password=get_password_hash(f"{suffix}pass"),
        full_name=f"User {suffix}",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, username, password):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _open_sinistre(db, test_user, test_product, test_hospital):
    _SEQ["n"] += 1
    seq = _SEQ["n"]
    product = test_product(db, code=f"MHC-WFC-{seq}", cout=Decimal("100.00"))
    subscription = Souscription(
        user_id=test_user.id,
        produit_assurance_id=product.id,
        numero_souscription=f"90{seq:04d}-10-011-001-2026",
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
        numero_alerte=f"ALT-WFC-{seq}",
        latitude=Decimal("48.8566"),
        longitude=Decimal("2.3522"),
        description="Urgence test workflow",
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


def _make_invoice(db, sinistre, statut=InvoiceStatus.PENDING_MEDICAL):
    stay = HospitalStay(
        sinistre_id=sinistre.id,
        hospital_id=sinistre.hospital_id,
        patient_id=sinistre.alerte.user_id,
        status="invoiced",
        started_at=datetime.utcnow(),
    )
    db.add(stay)
    db.flush()
    invoice = Invoice(
        hospital_id=sinistre.hospital_id,
        hospital_stay_id=stay.id,
        numero_facture=f"INV-WFC-{invoice_seq()}",
        montant_ht=Decimal("100000"),
        montant_tva=Decimal("18000"),
        montant_ttc=Decimal("118000"),
        date_facture=datetime.utcnow(),
        statut=statut,
        validation_medicale="pending" if statut == InvoiceStatus.PENDING_MEDICAL else "approved",
        validation_sinistre="pending" if statut == InvoiceStatus.PENDING_SINISTRE else None,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice, stay


_INV_SEQ = {"n": 0}


def invoice_seq():
    _INV_SEQ["n"] += 1
    return _INV_SEQ["n"]


class TestDecisionMedecinConseil:
    def test_accord_emits_no_document_and_unlocks_bpcu(
        self, db, test_user, test_product, test_hospital, test_doctor
    ):
        """Étape 2a : l'accord n'émet aucun bon mais autorise l'émission du 111."""
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)

        created = issue_decision_documents(db, sinistre, approve=True, actor=test_doctor, alerte=alerte)
        db.flush()
        assert created == []
        assert sinistre.decision_mc == "accord"
        assert sinistre.decision_mc_by_id == test_doctor.id
        assert "bpcu" in allowed_next_actions(sinistre)
        assert "brpcu" not in allowed_next_actions(sinistre)

        # La décision ne se reprend pas.
        try:
            issue_decision_documents(db, sinistre, approve=False, actor=test_doctor, alerte=alerte)
            assert False, "Une seconde décision devrait échouer"
        except ValueError:
            pass

    def test_refus_issues_112_and_closes(
        self, db, test_user, test_product, test_hospital, test_doctor
    ):
        """Étape 2b : le refus émet le bon 112 et clôt — sans validation pôle."""
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)

        created = issue_decision_documents(db, sinistre, approve=False, actor=test_doctor, alerte=alerte)
        db.flush()
        assert len(created) == 1
        brpcu = created[0]
        assert brpcu.document_type == "brpcu"
        assert "-112-" in brpcu.numero
        assert brpcu.validation_status == "non_requise"
        assert sinistre.decision_mc == "refus"
        assert sinistre.statut == "annule"
        assert alerte.statut == "annulee"

    def test_expired_bpcu_is_not_effective(
        self, db, test_user, test_product, test_hospital, test_doctor, test_receptionist
    ):
        """Un bon 111 expiré ne compte plus comme document effectif."""
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        sinistre.numero_sinistre = allocate_sinistre_number(db, sinistre)
        issue_decision_documents(db, sinistre, approve=True, actor=test_doctor, alerte=alerte)
        bpcu = issue_care_document(db, sinistre, "bpcu", test_receptionist, alerte=alerte)[0]
        db.flush()
        assert "bh" in allowed_next_actions(sinistre)

        bpcu.valid_until = datetime.utcnow() - timedelta(hours=1)
        db.flush()
        actions = allowed_next_actions(sinistre)
        assert "bh" not in actions  # le 111 expiré n'autorise plus l'hospitalisation
        assert "bpcu" in actions  # une réémission est proposée


class TestDeclarationManuelle:
    def test_declaration_creates_alerte_and_sinistre(
        self, client, db, test_user, test_product, test_hospital
    ):
        sinistre_ref, _, subscription = _open_sinistre(db, test_user, test_product, test_hospital)
        db.delete(sinistre_ref)
        db.commit()

        agent = _make_user(db, Role.AGENT_MEDICAL_MHC, "agentmed")
        headers = _login(client, "agentmed", "agentmedpass")

        found = client.get(f"/api/v1/sos/assures/search?q={test_user.email}", headers=headers)
        assert found.status_code == status.HTTP_200_OK
        results = found.json()
        assert any(r["id"] == test_user.id for r in results)
        assert results[0]["souscription_active"] is not None

        created = client.post(
            "/api/v1/sos/declaration-manuelle",
            json={"user_id": test_user.id, "description": "Appel au centre", "priorite": "urgente"},
            headers=headers,
        )
        assert created.status_code == status.HTTP_201_CREATED
        data = created.json()
        assert data["ok"] is True
        assert data["sinistre_id"] is not None
        assert data["souscription_trouvee"] is True

        alerte = db.query(Alerte).filter(Alerte.id == data["alerte_id"]).first()
        assert alerte.statut == "en_cours"
        sinistre = db.query(Sinistre).filter(Sinistre.id == data["sinistre_id"]).first()
        assert sinistre is not None
        assert sinistre.souscription_id == subscription.id

    def test_declaration_forbidden_for_regular_user(self, client, db, test_user, auth_headers):
        r = client.post(
            "/api/v1/sos/declaration-manuelle",
            json={"user_id": test_user.id},
            headers=auth_headers,
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

        s = client.get("/api/v1/sos/assures/search?q=test", headers=auth_headers)
        assert s.status_code == status.HTTP_403_FORBIDDEN


class TestInvoiceWorkflow:
    def test_full_chain_medical_affaires_paiement(
        self, client, db, test_user, test_product, test_hospital, test_doctor
    ):
        """Étapes 9-11 : médecin-conseil → affaires médicales → paiement MHC."""
        sinistre, alerte, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        invoice, stay = _make_invoice(db, sinistre)

        mc_headers = _login(client, "doctor", "doctorpassword123")
        sos_user = _make_user(db, Role.SOS_OPERATOR, "sosinv")
        sos_headers = _login(client, "sosinv", "sosinvpass")
        affaires = _make_user(db, Role.SUPERVISEUR_AFFAIRES_MEDICALES, "affaires")
        affaires_headers = _login(client, "affaires", "affairespass")
        compta = _make_user(db, Role.AGENT_COMPTABLE_MH, "compta")
        compta_headers = _login(client, "compta", "comptapass")

        # 1re validation : réservée au médecin-conseil (l'opérateur SOS est refusé).
        r = client.post(
            f"/api/v1/invoices/{invoice.id}/validate_medical",
            json={"approve": True},
            headers=sos_headers,
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

        r = client.post(
            f"/api/v1/invoices/{invoice.id}/validate_medical",
            json={"approve": True},
            headers=mc_headers,
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["statut"] == "pending_sinistre"

        # 2e validation : réservée aux affaires médicales (SOS refusé).
        r = client.post(
            f"/api/v1/invoices/{invoice.id}/validate_sinistre",
            json={"approve": True},
            headers=sos_headers,
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

        r = client.post(
            f"/api/v1/invoices/{invoice.id}/validate_sinistre",
            json={"approve": True},
            headers=affaires_headers,
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["statut"] == "validated"  # plus d'étape comptable intermédiaire

        # Paiement : réservé à la finance MHC → dossier réglé et clôturé.
        r = client.post(
            f"/api/v1/invoices/{invoice.id}/pay",
            json={"approve": True},
            headers=sos_headers,
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

        r = client.post(
            f"/api/v1/invoices/{invoice.id}/pay",
            json={"approve": True},
            headers=compta_headers,
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["statut"] == "paid"
        db.expire_all()
        assert db.get(Sinistre, sinistre.id).statut == "resolu"
        assert db.get(Alerte, alerte.id).statut == "resolue"

    def test_bloquee_and_reassureur_gate_payment(
        self, client, db, test_user, test_product, test_hospital
    ):
        sinistre, _, _ = _open_sinistre(db, test_user, test_product, test_hospital)
        invoice, _ = _make_invoice(db, sinistre, statut=InvoiceStatus.VALIDATED)
        invoice.reassureur_agrement = "en_attente"
        db.commit()

        compta = _make_user(db, Role.FINANCE_MANAGER, "finman")
        compta_headers = _login(client, "finman", "finmanpass")

        # Agrément en attente → paiement refusé.
        r = client.post(f"/api/v1/invoices/{invoice.id}/pay", json={"approve": True}, headers=compta_headers)
        assert r.status_code == status.HTTP_400_BAD_REQUEST

        r = client.post(
            f"/api/v1/invoices/{invoice.id}/reassureur-agrement",
            json={"approve": True, "notes": "Accord SCGRE"},
            headers=compta_headers,
        )
        assert r.status_code == status.HTTP_200_OK

        # Facture bloquée → paiement refusé, déblocage → paiement possible.
        r = client.post(f"/api/v1/invoices/{invoice.id}/block", json={"bloquee": True}, headers=compta_headers)
        assert r.status_code == status.HTTP_200_OK
        r = client.post(f"/api/v1/invoices/{invoice.id}/pay", json={"approve": True}, headers=compta_headers)
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        r = client.post(f"/api/v1/invoices/{invoice.id}/block", json={"bloquee": False}, headers=compta_headers)
        assert r.status_code == status.HTTP_200_OK

        r = client.post(f"/api/v1/invoices/{invoice.id}/pay", json={"approve": True}, headers=compta_headers)
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["statut"] == "paid"
