from datetime import datetime, timedelta
from decimal import Decimal

from app.core.enums import StatutSouscription
from app.models.attestation import Attestation
from app.models.souscription import Souscription


def _create_subscription(db, user, product):
    subscription = Souscription(
        user_id=user.id,
        produit_assurance_id=product.id,
        numero_souscription="SUB-ECARD-001",
        prix_applique=product.cout,
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutSouscription.ACTIVE,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def _attach_attestation(db, subscription):
    attestation = Attestation(
        souscription_id=subscription.id,
        paiement_id=None,
        type_attestation="definitive",
        numero_attestation="ATT-ECARD-001",
        chemin_fichier_minio="INLINE_PDF",
        bucket_minio="inline",
        url_signee="data:application/pdf;base64,AAA",
        carte_numerique_path="INLINE_CARD",
        carte_numerique_bucket="inline",
        carte_numerique_url="data:image/png;base64,AAA",
        carte_numerique_expires_at=datetime.utcnow() + timedelta(hours=1),
        est_valide=True,
    )
    db.add(attestation)
    db.commit()
    db.refresh(attestation)
    return attestation


def test_get_subscription_ecard_success(
    client, db, test_user, test_product, auth_headers
):
    product = test_product(db, code="ECARD-001", cout=Decimal("150.00"))
    subscription = _create_subscription(db, test_user, product)
    _attach_attestation(db, subscription)

    response = client.get(
        f"/api/v1/subscriptions/{subscription.id}/ecard",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["subscription_id"] == subscription.id
    assert data["holder_name"] == test_user.full_name
    assert data["card_url"].startswith("data:image/png")
    assert data["numero_souscription"] == subscription.numero_souscription


def test_get_subscription_ecard_not_available(
    client, db, test_user, test_product, auth_headers
):
    product = test_product(db, code="ECARD-002", cout=Decimal("120.00"))
    subscription = _create_subscription(db, test_user, product)

    response = client.get(
        f"/api/v1/subscriptions/{subscription.id}/ecard",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_get_subscription_ecard_for_other_user(
    client, db, test_user, test_admin, test_product, admin_headers
):
    product = test_product(db, code="ECARD-003", cout=Decimal("99.00"))
    subscription = _create_subscription(db, test_user, product)
    _attach_attestation(db, subscription)

    response = client.get(
        f"/api/v1/subscriptions/{subscription.id}/ecard",
        headers=admin_headers,
    )
    assert response.status_code == 404

