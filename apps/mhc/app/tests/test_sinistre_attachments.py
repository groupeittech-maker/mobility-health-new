import io
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import status

from app.core.config import settings
from app.models.alerte import Alerte
from app.models.hospital_stay import HospitalStay
from app.models.sinistre import Sinistre
from app.models.sinistre_attachment import SinistreAttachment, ATTACHMENT_CERTIFICAT_DECES


def _create_sinistre_with_stay(db, test_user, test_hospital, hospital_doctor):
    alerte = Alerte(
        user_id=test_user.id,
        souscription_id=None,
        numero_alerte="ALERT-CERT-DECES",
        latitude=Decimal("5.0"),
        longitude=Decimal("-3.0"),
        description="Test certificat décès",
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
        numero_sinistre="SIN-CERT-DECES",
        statut="en_cours",
        description="Sinistre test certificat",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(sinistre)
    db.commit()
    db.refresh(sinistre)

    stay = HospitalStay(
        sinistre_id=sinistre.id,
        hospital_id=test_hospital.id,
        patient_id=test_user.id,
        assigned_doctor_id=hospital_doctor.id,
        status="in_progress",
        report_status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(stay)
    db.commit()
    db.refresh(stay)
    return alerte, sinistre, stay


@pytest.fixture
def attachment_storage_root(tmp_path, monkeypatch):
    root = tmp_path / "uploads"
    root.mkdir()
    monkeypatch.setattr(settings, "LOCAL_FILE_STORAGE_ROOT", str(root))
    return root


class TestSinistreCertificatDecesAttachment:
    def test_assigned_doctor_can_upload_and_download(
        self,
        client,
        db,
        test_user,
        test_hospital,
        hospital_doctor,
        hospital_doctor_headers,
        attachment_storage_root,
    ):
        _, sinistre, _ = _create_sinistre_with_stay(db, test_user, test_hospital, hospital_doctor)
        pdf_bytes = b"%PDF-1.4 test certificat deces"

        upload = client.post(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/attachments/certificat-deces",
            files={"file": ("certificat-deces.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=hospital_doctor_headers,
        )
        assert upload.status_code == status.HTTP_201_CREATED
        data = upload.json()
        assert data["attachment_type"] == ATTACHMENT_CERTIFICAT_DECES
        assert data["file_name"] == "certificat-deces.pdf"
        assert data["file_size"] == len(pdf_bytes)

        download = client.get(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/attachments/certificat-deces",
            headers=hospital_doctor_headers,
        )
        assert download.status_code == status.HTTP_200_OK
        assert download.content == pdf_bytes

        stored = db.query(SinistreAttachment).filter(SinistreAttachment.sinistre_id == sinistre.id).all()
        assert len(stored) == 1

    def test_non_assigned_doctor_cannot_upload(
        self,
        client,
        db,
        test_user,
        test_hospital,
        hospital_doctor,
        reception_headers,
        attachment_storage_root,
    ):
        _, sinistre, _ = _create_sinistre_with_stay(db, test_user, test_hospital, hospital_doctor)

        upload = client.post(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/attachments/certificat-deces",
            files={"file": ("certificat.pdf", io.BytesIO(b"%PDF-test"), "application/pdf")},
            headers=reception_headers,
        )
        assert upload.status_code == status.HTTP_403_FORBIDDEN

    def test_sinistre_detail_includes_certificat_deces(
        self,
        client,
        db,
        test_user,
        test_hospital,
        hospital_doctor,
        hospital_doctor_headers,
        hospital_referent,
        hospital_referent_headers,
        attachment_storage_root,
    ):
        alerte, sinistre, _ = _create_sinistre_with_stay(db, test_user, test_hospital, hospital_doctor)
        sinistre.medecin_referent_id = hospital_referent.id
        db.commit()

        upload = client.post(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/attachments/certificat-deces",
            files={"file": ("acte-deces.pdf", io.BytesIO(b"%PDF-acte"), "application/pdf")},
            headers=hospital_doctor_headers,
        )
        assert upload.status_code == status.HTTP_201_CREATED

        detail = client.get(
            f"/api/v1/sos/{alerte.id}/sinistre",
            headers=hospital_referent_headers,
        )
        assert detail.status_code == status.HTTP_200_OK
        payload = detail.json()
        assert payload["certificat_deces"] is not None
        assert payload["certificat_deces"]["file_name"] == "acte-deces.pdf"

    def test_upload_replaces_existing_attachment(
        self,
        client,
        db,
        test_user,
        test_hospital,
        hospital_doctor,
        hospital_doctor_headers,
        attachment_storage_root,
    ):
        _, sinistre, _ = _create_sinistre_with_stay(db, test_user, test_hospital, hospital_doctor)

        first = client.post(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/attachments/certificat-deces",
            files={"file": ("v1.pdf", io.BytesIO(b"%PDF-v1"), "application/pdf")},
            headers=hospital_doctor_headers,
        )
        assert first.status_code == status.HTTP_201_CREATED

        second = client.post(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/attachments/certificat-deces",
            files={"file": ("v2.pdf", io.BytesIO(b"%PDF-v2"), "application/pdf")},
            headers=hospital_doctor_headers,
        )
        assert second.status_code == status.HTTP_201_CREATED
        assert second.json()["file_name"] == "v2.pdf"

        stored = db.query(SinistreAttachment).filter(SinistreAttachment.sinistre_id == sinistre.id).all()
        assert len(stored) == 1

        download = client.get(
            f"/api/v1/hospital-sinistres/sinistres/{sinistre.id}/attachments/certificat-deces",
            headers=hospital_doctor_headers,
        )
        assert download.content == b"%PDF-v2"
