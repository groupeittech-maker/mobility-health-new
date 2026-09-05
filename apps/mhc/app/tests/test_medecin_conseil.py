"""Coordonnées du médecin-conseil associées à la destination de souscription."""
import os
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import status

from fastapi import HTTPException

from app.core.enums import Role, StatutSouscription
from app.core.security import get_password_hash
from app.models.destination import DestinationCountry
from app.models.projet_voyage import ProjetVoyage
from app.models.souscription import Souscription
from app.models.user import User
from app.services.medecin_conseil import (
    ensure_medecin_conseil,
    list_medecin_conseil_for_user,
    serialize_medecin_conseil,
)


def _create_country(db, *, code="FR", nom="France", medecin_conseil_id=None):
    country = DestinationCountry(
        code=code,
        nom=nom,
        est_actif=True,
        ordre_affichage=0,
        medecin_conseil_id=medecin_conseil_id,
    )
    db.add(country)
    db.commit()
    db.refresh(country)
    return country


def _create_subscription(db, user, product, country, destination="Paris"):
    projet = ProjetVoyage(
        user_id=user.id,
        titre="Voyage test",
        destination=destination,
        destination_country_id=country.id,
        date_depart=datetime.utcnow() + timedelta(days=7),
        date_retour=datetime.utcnow() + timedelta(days=14),
        nombre_participants=1,
    )
    db.add(projet)
    db.flush()
    subscription = Souscription(
        user_id=user.id,
        produit_assurance_id=product.id,
        projet_voyage_id=projet.id,
        numero_souscription=f"SUB-MC-{country.code}-{user.id}",
        prix_applique=product.cout,
        date_debut=datetime.utcnow() - timedelta(days=1),
        date_fin=datetime.utcnow() + timedelta(days=29),
        statut=StatutSouscription.ACTIVE,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


class TestMedecinConseilService:
    def test_serialize_and_list_for_subscription_destination(
        self,
        db,
        test_user,
        test_product,
        test_doctor,
    ):
        test_doctor.telephone = "+33987654321"
        db.commit()
        france = _create_country(db, code="FR", nom="France", medecin_conseil_id=test_doctor.id)
        other = User(
            email="other.doc@example.com",
            username="other_doc",
            hashed_password=get_password_hash("otherdoc123"),
            full_name="Autre Médecin",
            role=Role.MEDECIN_REFERENT_MH,
            telephone="+33111111111",
            is_active=True,
        )
        db.add(other)
        db.commit()
        _create_country(db, code="DE", nom="Allemagne", medecin_conseil_id=other.id)
        product = test_product(db, code="MC-PROD-001", cout=Decimal("100.00"))
        subscription = _create_subscription(db, test_user, product, france, destination="Paris")

        contact = serialize_medecin_conseil(test_doctor)
        assert contact["nom"] == "Doctor User"
        assert contact["telephone"] == "+33987654321"

        items = list_medecin_conseil_for_user(db, test_user)
        assert len(items) == 1
        assert items[0]["souscription_id"] == subscription.id
        assert items[0]["destination_country_name"] == "France"
        assert items[0]["medecin_conseil"]["id"] == test_doctor.id
        assert items[0]["medecin_conseil"]["telephone"] == "+33987654321"
        assert items[0]["medecin_conseil"]["id"] != other.id

    def test_destination_without_medecin_has_null_contact(self, db, test_user, test_product):
        country = _create_country(db, code="PT", nom="Portugal")
        product = test_product(db, code="MC-PROD-002", cout=Decimal("80.00"))
        _create_subscription(db, test_user, product, country, destination="Lisbonne")

        items = list_medecin_conseil_for_user(db, test_user)
        assert len(items) == 1
        assert items[0]["destination_country_name"] == "Portugal"
        assert items[0]["medecin_conseil"] is None

    def test_ensure_medecin_conseil_rejects_regular_user(self, db, test_user, test_doctor):
        assert ensure_medecin_conseil(db, test_doctor.id).id == test_doctor.id
        try:
            ensure_medecin_conseil(db, test_user.id)
            raise AssertionError("Un assuré ne doit pas être accepté comme médecin-conseil")
        except HTTPException as exc:
            assert exc.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL", "").startswith("postgresql"),
    reason="Le login HTTP utilise une syntaxe PostgreSQL (role::text)",
)
class TestMedecinConseilDestination:
    def test_admin_assigns_medecin_conseil_to_destination(
        self,
        client,
        db,
        admin_headers,
        test_doctor,
    ):
        test_doctor.telephone = "+33123456789"
        db.commit()
        country = _create_country(db, code="IT", nom="Italie")

        response = client.put(
            f"/api/v1/destinations/admin/countries/{country.id}",
            json={"medecin_conseil_id": test_doctor.id},
            headers=admin_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["medecin_conseil_id"] == test_doctor.id
        assert data["medecin_conseil"]["id"] == test_doctor.id
        assert data["medecin_conseil"]["nom"] == "Doctor User"
        assert data["medecin_conseil"]["telephone"] == "+33123456789"
        assert data["medecin_conseil"]["email"] == "doctor@example.com"

    def test_reject_non_doctor_as_medecin_conseil(
        self,
        client,
        db,
        admin_headers,
        test_user,
    ):
        country = _create_country(db, code="ES", nom="Espagne")
        response = client.put(
            f"/api/v1/destinations/admin/countries/{country.id}",
            json={"medecin_conseil_id": test_user.id},
            headers=admin_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "médecin-conseil" in response.json()["detail"].lower()

    def test_user_gets_medecin_conseil_of_subscription_destination(
        self,
        client,
        db,
        test_user,
        test_product,
        test_doctor,
        auth_headers,
    ):
        test_doctor.telephone = "+33987654321"
        db.commit()
        france = _create_country(db, code="FR", nom="France", medecin_conseil_id=test_doctor.id)
        other = User(
            email="other.doc@example.com",
            username="other_doc",
            hashed_password=get_password_hash("otherdoc123"),
            full_name="Autre Médecin",
            role=Role.MEDECIN_REFERENT_MH,
            telephone="+33111111111",
            is_active=True,
        )
        db.add(other)
        db.commit()
        _create_country(db, code="DE", nom="Allemagne", medecin_conseil_id=other.id)
        product = test_product(db, code="MC-PROD-001", cout=Decimal("100.00"))
        subscription = _create_subscription(db, test_user, product, france, destination="Paris")

        response = client.get("/api/v1/sos/medecin-conseil", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        items = response.json()
        assert len(items) == 1
        item = items[0]
        assert item["souscription_id"] == subscription.id
        assert item["destination_country_name"] == "France"
        assert item["medecin_conseil"]["nom"] == "Doctor User"
        assert item["medecin_conseil"]["telephone"] == "+33987654321"
        assert item["medecin_conseil"]["id"] == test_doctor.id
        assert item["medecin_conseil"]["id"] != other.id

    def test_destination_without_medecin_returns_null_contact(
        self,
        client,
        db,
        test_user,
        test_product,
        auth_headers,
    ):
        country = _create_country(db, code="PT", nom="Portugal")
        product = test_product(db, code="MC-PROD-002", cout=Decimal("80.00"))
        _create_subscription(db, test_user, product, country, destination="Lisbonne")

        response = client.get("/api/v1/sos/medecin-conseil", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        items = response.json()
        assert len(items) == 1
        assert items[0]["destination_country_name"] == "Portugal"
        assert items[0]["medecin_conseil"] is None

    def test_destination_list_includes_medecin_conseil(
        self,
        client,
        db,
        test_doctor,
        auth_headers,
    ):
        test_doctor.telephone = "+3344556677"
        db.commit()
        _create_country(db, code="BE", nom="Belgique", medecin_conseil_id=test_doctor.id)

        response = client.get(
            "/api/v1/destinations/countries?include_cities=false",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        belgium = next(item for item in response.json() if item["code"] == "BE")
        assert belgium["medecin_conseil"]["telephone"] == "+3344556677"
        assert belgium["medecin_conseil"]["nom"] == "Doctor User"
