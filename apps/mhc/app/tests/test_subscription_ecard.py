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


def _create_project_with_minors(db, user, *, child_only=False):
    from app.core.enums import StatutProjetVoyage
    from app.models.projet_voyage import ProjetVoyage

    projet = ProjetVoyage(
        user_id=user.id,
        titre="Voyage test",
        destination="Paris",
        date_depart=datetime.utcnow() + timedelta(days=10),
        date_retour=datetime.utcnow() + timedelta(days=20),
        statut=StatutProjetVoyage.EN_PLANIFICATION,
        notes="Pour un tiers: oui" if child_only else None,
        mineurs=[
            {
                "nom": "NDIAYE",
                "prenom": "Fatou",
                "date_naissance": "2018-05-01",
                "numero_passeport": "P111",
                "validite_passeport": "2030-01-01",
            },
            {
                "nom": "NDIAYE",
                "prenom": "Moussa",
                "date_naissance": "2020-09-15",
                "numero_passeport": "P222",
                "validite_passeport": "2030-01-01",
            },
        ],
    )
    db.add(projet)
    db.commit()
    db.refresh(projet)
    return projet


def test_ecard_members_adult_plus_children(
    client, db, test_user, test_product, auth_headers
):
    """Un voyageur adulte + 2 enfants → 3 membres, l'adulte en index 0."""
    product = test_product(db, code="ECARD-M1", cout=Decimal("150.00"))
    subscription = _create_subscription(db, test_user, product)
    projet = _create_project_with_minors(db, test_user)
    subscription.projet_voyage_id = projet.id
    db.commit()

    response = client.get(
        f"/api/v1/subscriptions/{subscription.id}/ecard/members",
        headers=auth_headers,
    )
    assert response.status_code == 200
    members = response.json()["members"]
    assert [m["index"] for m in members] == [0, 1, 2]
    assert members[0]["role"] == "adult"
    assert members[1]["role"] == "child"
    assert members[1]["name"] == "Fatou NDIAYE"
    assert members[2]["name"] == "Moussa NDIAYE"


def test_ecard_members_child_only(
    client, db, test_user, test_product, auth_headers
):
    """Souscription « enfants uniquement » (Pour un tiers) : les membres sont
    les enfants — l'adulte souscripteur n'est pas un voyageur assuré."""
    product = test_product(db, code="ECARD-M2", cout=Decimal("150.00"))
    subscription = _create_subscription(db, test_user, product)
    projet = _create_project_with_minors(db, test_user, child_only=True)
    subscription.projet_voyage_id = projet.id
    db.commit()

    response = client.get(
        f"/api/v1/subscriptions/{subscription.id}/ecard/members",
        headers=auth_headers,
    )
    assert response.status_code == 200
    members = response.json()["members"]
    assert len(members) == 2
    assert all(m["role"] == "child" for m in members)
    assert members[0]["name"] == "Fatou NDIAYE"


def test_download_member_child_card_generated(
    client, db, test_user, test_product, auth_headers
):
    """Télécharger la e-carte d'un enfant ne renvoie PAS la carte du parent :
    une carte est générée à la volée pour ce membre (PNG)."""
    product = test_product(db, code="ECARD-M3", cout=Decimal("150.00"))
    subscription = _create_subscription(db, test_user, product)
    projet = _create_project_with_minors(db, test_user)
    subscription.projet_voyage_id = projet.id
    db.commit()
    _attach_attestation(db, subscription)

    response = client.get(
        f"/api/v1/subscriptions/{subscription.id}/ecard/download?member=1",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert "Fatou" in response.headers.get("content-disposition", "")


def test_download_member_unknown_returns_404(
    client, db, test_user, test_product, auth_headers
):
    product = test_product(db, code="ECARD-M4", cout=Decimal("150.00"))
    subscription = _create_subscription(db, test_user, product)
    projet = _create_project_with_minors(db, test_user)
    subscription.projet_voyage_id = projet.id
    db.commit()
    _attach_attestation(db, subscription)

    response = client.get(
        f"/api/v1/subscriptions/{subscription.id}/ecard/download?member=42",
        headers=auth_headers,
    )
    assert response.status_code == 404

