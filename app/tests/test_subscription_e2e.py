"""
End-to-end subscription flow tests
Flow: create project -> choose product -> questionnaire -> payment -> attestation
"""
import pytest
from fastapi import status
from datetime import datetime, timedelta
from decimal import Decimal


@pytest.mark.subscription
@pytest.mark.e2e
class TestSubscriptionE2E:
    """Test complete subscription E2E flow"""
    
    def test_complete_subscription_flow(
        self, client, db, test_user, test_product, test_project, auth_headers
    ):
        """Test complete subscription flow from start to finish"""
        # Step 1: Create travel project (if not already created)
        project_data = {
            "user_id": test_user.id,
            "titre": "Vacation to Paris",
            "description": "Summer vacation",
            "destination": "Paris, France",
            "date_depart": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "date_retour": (datetime.utcnow() + timedelta(days=60)).isoformat(),
            "nombre_participants": 2,
            "questionnaire_type": "long",
        }
        
        project_response = client.post(
            "/api/v1/voyages/",
            json=project_data,
            headers=auth_headers
        )
        assert project_response.status_code == status.HTTP_201_CREATED
        project_id = project_response.json()["id"]
        
        # Step 2: Create product (if not already created)
        product = test_product(
            db,
            code="E2E-PROD-001",
            nom="E2E Test Product",
            cout=Decimal("150.00"),
            est_actif=True
        )
        
        # Step 3: Start subscription (choose product)
        subscription_response = client.post(
            "/api/v1/subscriptions/start",
            json={
                "produit_assurance_id": product.id,
                "projet_voyage_id": project_id,
                "notes": "E2E test subscription"
            },
            headers=auth_headers
        )
        assert subscription_response.status_code == status.HTTP_201_CREATED
        subscription_data = subscription_response.json()
        subscription_id = subscription_data["id"]
        assert subscription_data["statut"] == "en_attente"
        assert subscription_data["prix_applique"] == float(product.cout)
        assert subscription_data["produit_assurance_id"] == product.id
        assert subscription_data["projet_voyage_id"] == project_id
        
        # Step 4: Complete short questionnaire
        questionnaire_response = client.post(
            f"/api/v1/questionnaires/subscriptions/{subscription_id}/questionnaire/short",
            json={
                "age": 30,
                "destination": "France",
                "duree_sejour": 30,
                "type_voyage": "tourisme"
            },
            headers=auth_headers
        )
        assert questionnaire_response.status_code == status.HTTP_200_OK
        questionnaire_data = questionnaire_response.json()
        assert questionnaire_data["type_questionnaire"] == "short"
        assert questionnaire_data["statut"] == "complete"
        
        # Step 5: Complete long questionnaire
        long_questionnaire_response = client.post(
            f"/api/v1/questionnaires/subscriptions/{subscription_id}/questionnaire/long",
            json={
                "antecedents_medicaux": False,
                "medicaments_actuels": [],
                "allergies": [],
                "assurance_existante": False,
                "conditions_particulieres": "None"
            },
            headers=auth_headers
        )
        assert long_questionnaire_response.status_code == status.HTTP_200_OK
        
        # Step 6: Initiate payment
        payment_response = client.post(
            "/api/v1/payments/initiate",
            json={
                "subscription_id": subscription_id,
                "amount": float(subscription_data["prix_applique"]),
                "payment_type": "carte_bancaire"
            },
            headers=auth_headers
        )
        assert payment_response.status_code == status.HTTP_201_CREATED
        payment_data = payment_response.json()
        payment_id = payment_data["payment_id"]
        assert "payment_url" in payment_data
        assert payment_data["status"] == "en_attente"
        
        # Step 7: Simulate payment success via webhook
        webhook_response = client.post(
            "/api/v1/payments/webhook",
            json={
                "payment_id": payment_id,
                "external_reference": "EXT-REF-12345",
                "status": "success",
                "amount": float(subscription_data["prix_applique"])
            }
        )
        assert webhook_response.status_code == status.HTTP_200_OK
        
        # Wait a bit for background task (in real scenario, this would be async)
        import time
        time.sleep(0.5)
        
        # Step 8: Check payment status
        payment_status_response = client.get(
            f"/api/v1/payments/{payment_id}/status",
            headers=auth_headers
        )
        assert payment_status_response.status_code == status.HTTP_200_OK
        payment_status = payment_status_response.json()
        # Payment should be processed (status might be en_cours or valide)
        assert payment_status["status"] in ["en_cours", "valide"]
        
        # Step 9: Get attestations
        attestations_response = client.get(
            f"/api/v1/attestations/subscriptions/{subscription_id}/attestations",
            headers=auth_headers
        )
        assert attestations_response.status_code == status.HTTP_200_OK
        attestations = attestations_response.json()
        # Should have at least one attestation (provisoire)
        assert len(attestations) > 0
        attestation = attestations[0]
        assert attestation["type_attestation"] == "provisoire"
        assert "numero_attestation" in attestation
        
        # Step 10: Get attestation with signed URL
        attestation_id = attestation["id"]
        attestation_url_response = client.get(
            f"/api/v1/attestations/attestations/{attestation_id}",
            headers=auth_headers
        )
        assert attestation_url_response.status_code == status.HTTP_200_OK
        attestation_with_url = attestation_url_response.json()
        assert "url_signee" in attestation_with_url or attestation_with_url.get("url_signee") is not None
    
    def test_subscription_without_project(self, client, db, test_user, test_product, auth_headers):
        """Test subscription without travel project"""
        product = test_product(db, code="NO-PROJ-001", cout=Decimal("100.00"))
        
        subscription_response = client.post(
            "/api/v1/subscriptions/start",
            json={
                "produit_assurance_id": product.id,
                "notes": "Subscription without project"
            },
            headers=auth_headers
        )
        assert subscription_response.status_code == status.HTTP_201_CREATED
        subscription_data = subscription_response.json()
        assert subscription_data["projet_voyage_id"] is None
        assert subscription_data["statut"] == "en_attente"
    
    def test_subscription_inactive_product(self, client, db, test_user, auth_headers):
        """Test subscription with inactive product"""
        from app.models.produit_assurance import ProduitAssurance
        from app.core.enums import CleRepartition
        
        inactive_product = ProduitAssurance(
            code="INACTIVE-001",
            nom="Inactive Product",
            cout=Decimal("100.00"),
            cle_repartition=CleRepartition.FIXE,
            est_actif=False
        )
        db.add(inactive_product)
        db.commit()
        db.refresh(inactive_product)
        
        response = client.post(
            "/api/v1/subscriptions/start",
            json={
                "produit_assurance_id": inactive_product.id
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_subscription_nonexistent_product(self, client, auth_headers):
        """Test subscription with non-existent product"""
        response = client.post(
            "/api/v1/subscriptions/start",
            json={
                "produit_assurance_id": 99999
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_subscription_other_user_project(self, client, db, test_user, test_admin, test_product, auth_headers):
        """Test subscription with another user's project (should fail)"""
        # Create project for admin
        from app.models.projet_voyage import ProjetVoyage
        from app.core.enums import StatutProjetVoyage
        
        admin_project = ProjetVoyage(
            user_id=test_admin.id,
            titre="Admin Project",
            destination="Paris",
            date_depart=datetime.utcnow() + timedelta(days=30),
            statut=StatutProjetVoyage.EN_PLANIFICATION
        )
        db.add(admin_project)
        db.commit()
        db.refresh(admin_project)
        
        product = test_product(db, code="OTHER-USER-001", cout=Decimal("100.00"))
        
        response = client.post(
            "/api/v1/subscriptions/start",
            json={
                "produit_assurance_id": product.id,
                "projet_voyage_id": admin_project.id
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_questionnaire_before_subscription(self, client, auth_headers):
        """Test questionnaire creation before subscription exists"""
        response = client.post(
            "/api/v1/questionnaires/subscriptions/99999/questionnaire/short",
            json={"age": 30},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_payment_before_subscription(self, client, auth_headers):
        """Test payment initiation before subscription exists"""
        response = client.post(
            "/api/v1/payments/initiate",
            json={
                "subscription_id": 99999,
                "amount": 100.00,
                "payment_type": "carte_bancaire"
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_payment_already_paid_subscription(self, client, db, test_user, test_product, auth_headers):
        """Test payment for already paid subscription"""
        from app.models.souscription import Souscription
        from app.core.enums import StatutSouscription
        
        product = test_product(db, code="PAID-001", cout=Decimal("100.00"))
        
        # Create active subscription
        subscription = Souscription(
            user_id=test_user.id,
            produit_assurance_id=product.id,
            numero_souscription="SUB-TEST-001",
            prix_applique=product.cout,
            date_debut=datetime.utcnow(),
            statut=StatutSouscription.ACTIVE
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        response = client.post(
            "/api/v1/payments/initiate",
            json={
                "subscription_id": subscription.id,
                "amount": 100.00,
                "payment_type": "carte_bancaire"
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already paid" in response.json()["detail"].lower()
    
    def test_get_subscriptions_list(self, client, db, test_user, test_product, auth_headers):
        """Test getting user's subscriptions list"""
        product = test_product(db, code="LIST-001", cout=Decimal("100.00"))
        
        # Create a subscription
        subscription_response = client.post(
            "/api/v1/subscriptions/start",
            json={
                "produit_assurance_id": product.id
            },
            headers=auth_headers
        )
        assert subscription_response.status_code == status.HTTP_201_CREATED
        
        # Get subscriptions list
        list_response = client.get(
            "/api/v1/subscriptions/",
            headers=auth_headers
        )
        assert list_response.status_code == status.HTTP_200_OK
        subscriptions = list_response.json()
        assert len(subscriptions) > 0
        assert any(s["id"] == subscription_response.json()["id"] for s in subscriptions)
    
    def test_get_subscription_by_id(self, client, db, test_user, test_product, auth_headers):
        """Test getting a specific subscription"""
        product = test_product(db, code="GET-001", cout=Decimal("100.00"))
        
        # Create subscription
        subscription_response = client.post(
            "/api/v1/subscriptions/start",
            json={
                "produit_assurance_id": product.id
            },
            headers=auth_headers
        )
        subscription_id = subscription_response.json()["id"]
        
        # Get subscription
        get_response = client.get(
            f"/api/v1/subscriptions/{subscription_id}",
            headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_200_OK
        subscription = get_response.json()
        assert subscription["id"] == subscription_id
        assert subscription["produit_assurance_id"] == product.id





