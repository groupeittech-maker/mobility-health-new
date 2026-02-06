from decimal import Decimal
from datetime import datetime

from fastapi import status

from app.models.alerte import Alerte
from app.models.invoice import Invoice
from app.models.sinistre import Sinistre


def _create_sinistre(db, test_user, test_hospital):
    alerte = Alerte(
        user_id=test_user.id,
        souscription_id=None,
        numero_alerte="ALERT-TEST-ORIENTATION",
        latitude=Decimal("5.0"),
        longitude=Decimal("-3.0"),
        description="Test orientation",
        priorite="urgente",
        statut="en_cours",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(alerte)
    db.commit()
    db.refresh(alerte)

    sinistre = Sinistre(
        alerte_id=alerte.id,
        souscription_id=None,
        hospital_id=test_hospital.id,
        numero_sinistre="SIN-TEST-ORIENTATION",
        statut="en_cours",
        description="Sinistre pour test de séjour",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(sinistre)
    db.commit()
    db.refresh(sinistre)
    return alerte, sinistre


class TestHospitalStayFlow:
    def test_reception_can_dispatch_and_create_stay(
        self,
        client,
        db,
        test_user,
        test_hospital,
        reception_headers,
        hospital_doctor,
    ):
        _, sinistre = _create_sinistre(db, test_user, test_hospital)

        dispatch = client.post(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/dispatch-ambulance",
            json={"notes": "Test envoi ambulance"},
            headers=reception_headers,
        )
        assert dispatch.status_code == status.HTTP_200_OK
        dispatch_data = dispatch.json()
        assert dispatch_data["step_key"] == "ambulance_en_route"
        assert dispatch_data["statut"] in {"in_progress", "completed"}

        stay_response = client.post(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/stays",
            json={
                "doctor_id": hospital_doctor.id,
                "orientation_notes": "Patient attendu aux urgences",
            },
            headers=reception_headers,
        )
        assert stay_response.status_code == status.HTTP_201_CREATED
        stay_data = stay_response.json()
        assert stay_data["doctor_id"] == hospital_doctor.id
        assert stay_data["status"] == "in_progress"

    def test_doctor_can_submit_stay_report(
        self,
        client,
        db,
        test_user,
        test_hospital,
        reception_headers,
        hospital_doctor,
        hospital_doctor_headers,
    ):
        _, sinistre = _create_sinistre(db, test_user, test_hospital)

        stay = client.post(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/stays",
            json={"doctor_id": hospital_doctor.id},
            headers=reception_headers,
        )
        assert stay.status_code == status.HTTP_201_CREATED
        stay_id = stay.json()["id"]

        report_payload = {
            "motif_consultation": "Traumatisme",
            "motif_hospitalisation": "Surveillance",
            "duree_sejour_heures": 6,
            "actes_effectues": ["Consultation médicale"],
            "examens_effectues": ["Analyse sanguine"],
            "resume": "Patient stabilisé",
            "observations": "Retour à domicile envisageable",
            "terminer_sejour": True,
        }
        report_response = client.put(
            f"/api/v1/hospital-sinistres/hospital-stays/{stay_id}/report",
            json=report_payload,
            headers=hospital_doctor_headers,
        )
        assert report_response.status_code == status.HTTP_200_OK
        report_data = report_response.json()
        assert report_data["status"] == "awaiting_validation"
        assert report_data["report_status"] == "submitted"
        assert report_data["report_actes"] == ["Consultation médicale"]
        assert report_data["report_examens"] == ["Analyse sanguine"]

    def test_referent_validation_and_invoice_flow(
        self,
        client,
        db,
        test_user,
        test_hospital,
        reception_headers,
        hospital_doctor,
        hospital_doctor_headers,
        hospital_referent_headers,
        hospital_accountant_headers,
        sos_operator_headers,
    ):
        _, sinistre = _create_sinistre(db, test_user, test_hospital)
        stay = client.post(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/stays",
            json={"doctor_id": hospital_doctor.id},
            headers=reception_headers,
        )
        stay_id = stay.json()["id"]

        report_response = client.put(
            f"/api/v1/hospital-sinistres/hospital-stays/{stay_id}/report",
            json={
                "motif_consultation": "Traumatisme",
                "motif_hospitalisation": "Surveillance",
                "duree_sejour_heures": 6,
                "actes_effectues": ["Consultation médicale"],
                "examens_effectues": ["Analyse sanguine"],
                "resume": "Patient stabilisé",
                "observations": "RAS",
                "terminer_sejour": True,
            },
            headers=hospital_doctor_headers,
        )
        assert report_response.status_code == status.HTTP_200_OK
        assert report_response.json()["status"] == "awaiting_validation"

        validation = client.post(
            f"/api/v1/hospital-sinistres/hospital-stays/{stay_id}/validation",
            json={"approve": True, "notes": "Prise en charge validée"},
            headers=hospital_referent_headers,
        )
        assert validation.status_code == status.HTTP_200_OK
        assert validation.json()["status"] == "validated"
        assert validation.json()["report_status"] == "approved"

        invoice = client.post(
            f"/api/v1/hospital-sinistres/hospital-stays/{stay_id}/invoice",
            json={"taux_tva": 0.18},
            headers=hospital_accountant_headers,
        )
        assert invoice.status_code == status.HTTP_200_OK
        invoice_data = invoice.json()
        assert invoice_data["status"] == "invoiced"
        assert invoice_data["invoice"] is not None
        invoice_id = invoice_data["invoice"]["id"]

        medical_validation = client.post(
            f"/api/v1/invoices/{invoice_id}/validate_medical",
            json={"approve": True, "notes": "Facture conforme"},
            headers=hospital_referent_headers,
        )
        assert medical_validation.status_code == status.HTTP_200_OK
        medical_payload = medical_validation.json()
        assert medical_payload["statut"] == "pending_sinistre"
        assert medical_payload["validation_medicale"] == "approved"

        invoice_list = client.get(
            "/api/v1/invoices?stage=sinistre",
            headers=sos_operator_headers,
        )
        assert invoice_list.status_code == status.HTTP_200_OK
        invoice_list_data = invoice_list.json()
        assert any(item["id"] == invoice_id for item in invoice_list_data)

        history_response = client.get(
            f"/api/v1/invoices/{invoice_id}/history",
            headers=hospital_referent_headers,
        )
        assert history_response.status_code == status.HTTP_200_OK
        history_entries = history_response.json()
        assert len(history_entries) >= 2
        actions = [entry["action"] for entry in history_entries]
        assert "invoice_created" in actions
        assert any(action.startswith("medical_validation") for action in actions)

    def test_accountant_can_submit_custom_invoice_lines(
        self,
        client,
        db,
        test_user,
        test_hospital,
        reception_headers,
        hospital_doctor,
        hospital_doctor_headers,
        hospital_referent_headers,
        hospital_accountant_headers,
    ):
        _, sinistre = _create_sinistre(db, test_user, test_hospital)
        stay = client.post(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/stays",
            json={"doctor_id": hospital_doctor.id},
            headers=reception_headers,
        )
        stay_id = stay.json()["id"]

        report_response = client.put(
            f"/api/v1/hospital-sinistres/hospital-stays/{stay_id}/report",
            json={
                "motif_consultation": "Observation",
                "motif_hospitalisation": "Traumatisme",
                "duree_sejour_heures": 4,
                "actes_effectues": ["Consultation médicale"],
                "examens_effectues": [],
                "terminer_sejour": True,
            },
            headers=hospital_doctor_headers,
        )
        assert report_response.status_code == status.HTTP_200_OK

        validation = client.post(
            f"/api/v1/hospital-sinistres/hospital-stays/{stay_id}/validation",
            json={"approve": True, "notes": "RAS"},
            headers=hospital_referent_headers,
        )
        assert validation.status_code == status.HTTP_200_OK

        custom_lines = [
            {"libelle": "Acte spécial", "quantite": 2, "prix_unitaire": 10000},
            {"libelle": "Analyse complémentaire", "quantite": 1, "prix_unitaire": 5000},
        ]
        invoice_response = client.post(
            f"/api/v1/hospital-sinistres/hospital-stays/{stay_id}/invoice",
            json={
                "taux_tva": 0.2,
                "notes": "Facturation manuelle",
                "lines": custom_lines,
            },
            headers=hospital_accountant_headers,
        )
        assert invoice_response.status_code == status.HTTP_200_OK
        invoice_payload = invoice_response.json()
        assert invoice_payload["status"] == "invoiced"
        assert invoice_payload["invoice"] is not None
        invoice_summary = invoice_payload["invoice"]
        invoice_id = invoice_summary["id"]
        montant_ttc = Decimal(str(invoice_summary["montant_ttc"]))
        assert montant_ttc == Decimal("30000")

        db.expire_all()
        db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        assert db_invoice is not None
        assert len(db_invoice.items) == len(custom_lines)
        labels = {item.libelle for item in db_invoice.items}
        assert {"Acte spécial", "Analyse complémentaire"}.issubset(labels)
        assert any(item.quantite == 2 for item in db_invoice.items)

