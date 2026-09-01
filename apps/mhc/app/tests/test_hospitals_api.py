import uuid
from decimal import Decimal
from fastapi import status

from app.models.user import User
from app.models.alerte import Alerte
from app.models.sinistre import Sinistre
from app.models.hospital import Hospital
from app.core.enums import Role
from app.core.security import get_password_hash


class TestHospitalAPI:
    def test_create_hospital_with_assignments(
        self,
        client,
        db,
        admin_headers,
        test_doctor,
        test_receptionist
    ):
        payload = {
            "nom": "Test Clinic",
            "adresse": "1 Test Street",
            "ville": "Test City",
            "pays": "Testland",
            "latitude": 5.1234,
            "longitude": -3.9876,
            "est_actif": True,
            "medecin_referent_id": test_doctor.id,
            "receptionist_ids": [test_receptionist.id],
        }
        response = client.post(
            "/api/v1/hospitals/",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["medecin_referent_id"] == test_doctor.id
        assert data["receptionists_count"] == 1
        db.refresh(test_receptionist)
        assert test_receptionist.hospital_id == data["id"]

    def test_update_hospital_assignments(
        self,
        client,
        db,
        admin_headers,
        test_doctor,
        test_receptionist
    ):
        # Create hospital without assignments
        payload = {
            "nom": "Second Clinic",
            "adresse": "2 Test Street",
            "ville": "Test City",
            "pays": "Testland",
            "latitude": 5.5,
            "longitude": -3.5,
            "est_actif": True,
        }
        create_response = client.post(
            "/api/v1/hospitals/",
            json=payload,
            headers=admin_headers
        )
        hospital_id = create_response.json()["id"]

        # Create additional receptionist
        new_receptionist = User(
            email="second.reception@example.com",
            username="second_reception",
            hashed_password=get_password_hash("reception456"),
            full_name="Second Receptionist",
            role=Role.AGENT_RECEPTION_HOPITAL,
            is_active=True,
        )
        db.add(new_receptionist)
        db.commit()
        db.refresh(new_receptionist)

        update_payload = {
            "medecin_referent_id": test_doctor.id,
            "receptionist_ids": [new_receptionist.id],
        }
        update_response = client.put(
            f"/api/v1/hospitals/{hospital_id}",
            json=update_payload,
            headers=admin_headers
        )
        assert update_response.status_code == status.HTTP_200_OK
        updated = update_response.json()
        assert updated["medecin_referent_id"] == test_doctor.id
        assert updated["receptionists_count"] == 1

        db.refresh(test_receptionist)
        assert test_receptionist.hospital_id is None
        db.refresh(new_receptionist)
        assert new_receptionist.hospital_id == hospital_id

    def test_receptionist_can_view_assigned_alerts(
        self,
        client,
        db,
        test_user,
        test_hospital,
        test_receptionist
    ):
        test_receptionist.hospital_id = test_hospital.id
        db.commit()
        db.refresh(test_receptionist)

        alerte, _ = create_alert_with_sinistre(db, test_user, test_hospital)

        token = login(client, "reception", "reception123")
        response = client.get(
            "/api/v1/sos/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["assigned_hospital"]["id"] == test_hospital.id
        assert data[0]["user_full_name"] == test_user.full_name
        assert data[0]["user_email"] == test_user.email

    def test_medecin_referent_can_view_alert_detail(
        self,
        client,
        db,
        test_user,
        test_hospital,
        test_doctor
    ):
        test_hospital.medecin_referent_id = test_doctor.id
        db.commit()
        db.refresh(test_hospital)

        alerte, _ = create_alert_with_sinistre(db, test_user, test_hospital)

        token = login(client, "doctor", "doctorpassword123")
        detail_response = client.get(
            f"/api/v1/sos/{alerte.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert detail_response.status_code == status.HTTP_200_OK

        sinistre_response = client.get(
            f"/api/v1/sos/{alerte.id}/sinistre",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert sinistre_response.status_code == status.HTTP_200_OK
        sinistre_data = sinistre_response.json()
        assert sinistre_data["patient"]["id"] == test_user.id
        assert sinistre_data["hospital"]["id"] == test_hospital.id

    def test_admin_can_assign_hospital_doctors(
        self,
        client,
        db,
        admin_headers,
        test_hospital,
        hospital_doctor
    ):
        hospital_doctor.hospital_id = None
        db.commit()
        db.refresh(hospital_doctor)

        update_response = client.put(
            f"/api/v1/hospitals/{test_hospital.id}",
            json={"doctor_ids": [hospital_doctor.id]},
            headers=admin_headers
        )
        assert update_response.status_code == status.HTTP_200_OK

        db.refresh(hospital_doctor)
        assert hospital_doctor.hospital_id == test_hospital.id


def login(client, username, password):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password}
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]


def create_alert_with_sinistre(db, user, hospital):
    numero = f"ALERT-TEST-{uuid.uuid4().hex[:6].upper()}"
    alerte = Alerte(
        user_id=user.id,
        souscription_id=None,
        numero_alerte=numero,
        latitude=Decimal("5.0"),
        longitude=Decimal("-3.0"),
        priorite="urgente",
        statut="en_cours"
    )
    db.add(alerte)
    db.commit()
    db.refresh(alerte)

    sinistre = Sinistre(
        alerte_id=alerte.id,
        hospital_id=hospital.id,
        numero_sinistre=f"SIN-TEST-{uuid.uuid4().hex[:6].upper()}",
        statut="en_cours"
    )
    db.add(sinistre)
    db.commit()
    db.refresh(sinistre)
    return alerte, sinistre

