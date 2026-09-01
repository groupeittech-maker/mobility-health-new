"""
SOS flow tests
Flow: trigger -> agent reception -> create sinistre
"""
import pytest
from fastapi import status
from decimal import Decimal
from datetime import datetime, timedelta

PARIS_LAT = float(Decimal("48.8566"))
PARIS_LON = float(Decimal("2.3522"))


@pytest.mark.sos
@pytest.mark.e2e
class TestSOSFlow:
    """Test SOS flow from trigger to sinistre creation"""
    
    def test_complete_sos_flow(
        self,
        client,
        db,
        test_user,
        test_product,
        test_sos_operator,
        test_doctor,
        test_hospital,
        auth_headers,
        medecin_referent_headers,
    ):
        """Test complete SOS flow: trigger -> agent reception -> sinistre creation"""
        from app.models.souscription import Souscription
        from app.core.enums import StatutSouscription
        
        # Step 1: Create an active subscription
        product = test_product(db, code="SOS-PROD-001", cout=Decimal("100.00"))
        
        subscription = Souscription(
            user_id=test_user.id,
            produit_assurance_id=product.id,
            numero_souscription="SUB-SOS-001",
            prix_applique=product.cout,
            date_debut=datetime.utcnow() - timedelta(days=1),
            date_fin=datetime.utcnow() + timedelta(days=29),
            statut=StatutSouscription.ACTIVE
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        # Step 2: Trigger SOS alert
        sos_response = client.post(
            "/api/v1/sos/trigger",
            json={
                "souscription_id": subscription.id,
                "latitude": PARIS_LAT,
                "longitude": PARIS_LON,
                "adresse": "123 Test Street, Paris, France",
                "description": "Medical emergency - need assistance",
                "priorite": "haute"
            },
            headers=auth_headers
        )
        assert sos_response.status_code == status.HTTP_201_CREATED
        alerte_data = sos_response.json()
        alerte_id = alerte_data["id"]
        assert alerte_data["statut"] == "en_cours"
        assert alerte_data["priorite"] == "haute"
        assert alerte_data["souscription_id"] == subscription.id
        assert "numero_alerte" in alerte_data
        
        # Step 3: Verify sinistre was created
        from app.models.sinistre import Sinistre
        from app.models.sinistre_process_step import SinistreProcessStep
        sinistre = db.query(Sinistre).filter(Sinistre.alerte_id == alerte_id).first()
        assert sinistre is not None
        assert sinistre.statut == "en_cours"
        assert sinistre.souscription_id == subscription.id
        assert sinistre.numero_sinistre is None
        # Sinistre should be assigned to an agent if available
        if test_sos_operator:
            assert sinistre.agent_sinistre_id is not None
        
        # Step 4: Verify hospital was found
        assert sinistre.hospital_id is not None

        # Step 4bis: Workflow steps should exist
        steps = db.query(SinistreProcessStep).filter(SinistreProcessStep.sinistre_id == sinistre.id).all()
        assert len(steps) == 15
        keys = {step.step_key for step in steps}
        assert "alerte_declenchee" in keys
        assert "centre_ops_notifie" in keys
        assert "validation_et_numero_sinistre" in keys
        assert "validation_facture_medicale" in keys
        assert "validation_facture_sinistre" in keys
        
        # Step 5: Validation médicale attribue le numéro de sinistre
        verification = client.post(
            f"/api/v1/sos/sinistres/{sinistre.id}/verification",
            json={"approve": True, "notes": "Cas confirmé"},
            headers=medecin_referent_headers,
        )
        assert verification.status_code == status.HTTP_200_OK
        db.refresh(sinistre)
        assert sinistre.numero_sinistre is not None
        assert len(sinistre.numero_sinistre) > 0

        # Step 6: Get alertes list (as user)
        alertes_response = client.get(
            "/api/v1/sos/",
            headers=auth_headers
        )
        assert alertes_response.status_code == status.HTTP_200_OK
        alertes = alertes_response.json()
        assert len(alertes) > 0
        assert any(a["id"] == alerte_id for a in alertes)
        
        # Step 7: Get specific alerte
        alerte_detail_response = client.get(
            f"/api/v1/sos/{alerte_id}",
            headers=auth_headers
        )
        assert alerte_detail_response.status_code == status.HTTP_200_OK
        alerte_detail = alerte_detail_response.json()
        assert alerte_detail["id"] == alerte_id
        assert alerte_detail["description"] == "Medical emergency - need assistance"

        # Step 8: Get sinistre detail and ensure workflow is exposed
        sinistre_detail_response = client.get(
            f"/api/v1/sos/{alerte_id}/sinistre",
            headers=auth_headers,
        )
        assert sinistre_detail_response.status_code == status.HTTP_200_OK
        sinistre_detail = sinistre_detail_response.json()
        assert sinistre_detail["id"] == sinistre.id
        assert "workflow_steps" in sinistre_detail
        assert len(sinistre_detail["workflow_steps"]) == 15
        first_step = sinistre_detail["workflow_steps"][0]
        assert first_step["step_key"] == "alerte_declenchee"
        assert first_step["statut"] == "completed"
    
    def test_sos_trigger_without_active_subscription(self, client, db, test_user, auth_headers):
        """Test SOS trigger without active subscription"""
        response = client.post(
            "/api/v1/sos/trigger",
            json={
                "latitude": PARIS_LAT,
                "longitude": PARIS_LON,
                "adresse": "123 Test Street",
                "description": "Emergency",
                "priorite": "haute"
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "souscription active" in response.json()["detail"].lower()
    
    def test_sos_trigger_with_specific_subscription(self, client, db, test_user, test_product, auth_headers):
        """Test SOS trigger with specific subscription ID"""
        from app.models.souscription import Souscription
        from app.core.enums import StatutSouscription
        
        product = test_product(db, code="SOS-SPEC-001", cout=Decimal("100.00"))
        
        subscription = Souscription(
            user_id=test_user.id,
            produit_assurance_id=product.id,
            numero_souscription="SUB-SPEC-001",
            prix_applique=product.cout,
            date_debut=datetime.utcnow() - timedelta(days=1),
            statut=StatutSouscription.ACTIVE
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        response = client.post(
            "/api/v1/sos/trigger",
            json={
                "souscription_id": subscription.id,
                "latitude": PARIS_LAT,
                "longitude": PARIS_LON,
                "adresse": "123 Test Street",
                "description": "Emergency with specific subscription",
                "priorite": "moyenne"
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["souscription_id"] == subscription.id
    
    def test_sos_trigger_unauthorized(self, client):
        """Test SOS trigger without authentication"""
        response = client.post(
            "/api/v1/sos/trigger",
            json={
                "latitude": PARIS_LAT,
                "longitude": PARIS_LON,
                "adresse": "123 Test Street",
                "description": "Emergency",
                "priorite": "haute"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_sos_get_alertes_as_user(self, client, db, test_user, test_product, auth_headers):
        """Test getting alertes list as regular user (should only see own alertes)"""
        from app.models.souscription import Souscription
        from app.models.alerte import Alerte
        from app.core.enums import StatutSouscription
        
        product = test_product(db, code="SOS-LIST-001", cout=Decimal("100.00"))
        
        subscription = Souscription(
            user_id=test_user.id,
            produit_assurance_id=product.id,
            numero_souscription="SUB-LIST-001",
            prix_applique=product.cout,
            date_debut=datetime.utcnow(),
            statut=StatutSouscription.ACTIVE
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        # Create alerte
        alerte = Alerte(
            user_id=test_user.id,
            souscription_id=subscription.id,
            numero_alerte="ALERT-TEST-001",
            latitude=Decimal("48.8566"),
            longitude=Decimal("2.3522"),
            adresse="Test Address",
            description="Test alert",
            priorite="moyenne",
            statut="en_cours"
        )
        db.add(alerte)
        db.commit()
        db.refresh(alerte)
        
        # Get alertes
        response = client.get(
            "/api/v1/sos/",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        alertes = response.json()
        # Should only see own alertes
        assert all(a["user_id"] == test_user.id for a in alertes)
    
    def test_sos_get_alertes_as_operator(self, client, db, test_user, test_sos_operator, test_product, sos_operator_headers):
        """Test getting alertes list as SOS operator (should see all alertes)"""
        from app.models.souscription import Souscription
        from app.models.alerte import Alerte
        from app.core.enums import StatutSouscription
        
        product = test_product(db, code="SOS-OP-001", cout=Decimal("100.00"))
        
        subscription = Souscription(
            user_id=test_user.id,
            produit_assurance_id=product.id,
            numero_souscription="SUB-OP-001",
            prix_applique=product.cout,
            date_debut=datetime.utcnow(),
            statut=StatutSouscription.ACTIVE
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        # Create alerte
        alerte = Alerte(
            user_id=test_user.id,
            souscription_id=subscription.id,
            numero_alerte="ALERT-OP-001",
            latitude=Decimal("48.8566"),
            longitude=Decimal("2.3522"),
            adresse="Test Address",
            description="Test alert for operator",
            priorite="haute",
            statut="en_cours"
        )
        db.add(alerte)
        db.commit()
        db.refresh(alerte)
        
        # Get alertes as operator
        response = client.get(
            "/api/v1/sos/",
            headers=sos_operator_headers
        )
        assert response.status_code == status.HTTP_200_OK
        alertes = response.json()
        # Operator should see all alertes
        assert len(alertes) > 0
        assert any(a["id"] == alerte.id for a in alertes)
    
    def test_sos_get_alerte_by_id(self, client, db, test_user, test_product, auth_headers):
        """Test getting a specific alerte by ID"""
        from app.models.souscription import Souscription
        from app.models.alerte import Alerte
        from app.core.enums import StatutSouscription
        
        product = test_product(db, code="SOS-GET-001", cout=Decimal("100.00"))
        
        subscription = Souscription(
            user_id=test_user.id,
            produit_assurance_id=product.id,
            numero_souscription="SUB-GET-001",
            prix_applique=product.cout,
            date_debut=datetime.utcnow(),
            statut=StatutSouscription.ACTIVE
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        alerte = Alerte(
            user_id=test_user.id,
            souscription_id=subscription.id,
            numero_alerte="ALERT-GET-001",
            latitude=Decimal("48.8566"),
            longitude=Decimal("2.3522"),
            adresse="Test Address",
            description="Test alert detail",
            priorite="moyenne",
            statut="en_cours"
        )
        db.add(alerte)
        db.commit()
        db.refresh(alerte)
        
        response = client.get(
            f"/api/v1/sos/{alerte.id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        alerte_data = response.json()
        assert alerte_data["id"] == alerte.id
        assert alerte_data["numero_alerte"] == "ALERT-GET-001"
    
    def test_sos_get_other_user_alerte_forbidden(self, client, db, test_user, test_admin, test_product, auth_headers):
        """Test getting another user's alerte (should be forbidden)"""
        from app.models.souscription import Souscription
        from app.models.alerte import Alerte
        from app.core.enums import StatutSouscription
        
        product = test_product(db, code="SOS-FORB-001", cout=Decimal("100.00"))
        
        # Create subscription for admin
        subscription = Souscription(
            user_id=test_admin.id,
            produit_assurance_id=product.id,
            numero_souscription="SUB-FORB-001",
            prix_applique=product.cout,
            date_debut=datetime.utcnow(),
            statut=StatutSouscription.ACTIVE
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        # Create alerte for admin
        alerte = Alerte(
            user_id=test_admin.id,
            souscription_id=subscription.id,
            numero_alerte="ALERT-FORB-001",
            latitude=Decimal("48.8566"),
            longitude=Decimal("2.3522"),
            adresse="Test Address",
            description="Admin alert",
            priorite="haute",
            statut="en_cours"
        )
        db.add(alerte)
        db.commit()
        db.refresh(alerte)
        
        # Try to get admin's alerte as regular user
        response = client.get(
            f"/api/v1/sos/{alerte.id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_sos_trigger_creates_sinistre(self, client, db, test_user, test_product, test_sos_operator, test_doctor, test_hospital, auth_headers):
        """Test that SOS trigger automatically creates sinistre"""
        from app.models.souscription import Souscription
        from app.models.questionnaire import Questionnaire
        from app.models.sinistre import Sinistre
        from app.core.enums import StatutSouscription
        
        product = test_product(db, code="SOS-SIN-001", cout=Decimal("100.00"))
        
        subscription = Souscription(
            user_id=test_user.id,
            produit_assurance_id=product.id,
            numero_souscription="SUB-SIN-001",
            prix_applique=product.cout,
            date_debut=datetime.utcnow() - timedelta(days=1),
            statut=StatutSouscription.ACTIVE
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        # Trigger SOS
        sos_response = client.post(
            "/api/v1/sos/trigger",
            json={
                "souscription_id": subscription.id,
                "latitude": PARIS_LAT,
                "longitude": PARIS_LON,
                "adresse": "123 Test Street",
                "description": "Emergency - sinistre test",
                "priorite": "haute"
            },
            headers=auth_headers
        )
        assert sos_response.status_code == status.HTTP_201_CREATED
        alerte_id = sos_response.json()["id"]
        
        # Verify sinistre was created
        sinistre = db.query(Sinistre).filter(Sinistre.alerte_id == alerte_id).first()
        assert sinistre is not None
        assert sinistre.alerte_id == alerte_id
        assert sinistre.souscription_id == subscription.id
        assert sinistre.statut == "en_cours"
        assert sinistre.hospital_id is not None  # Should find nearest hospital
        # Should be assigned to agent if available
        if test_sos_operator:
            assert sinistre.agent_sinistre_id is not None
        if test_doctor:
            assert sinistre.medecin_referent_id is not None

    def test_sos_sinistre_detail_contains_medical_questionnaire(
        self,
        client,
        db,
        test_user,
        test_product,
        test_sos_operator,
        test_doctor,
        test_hospital,
        auth_headers
    ):
        """Ensure the medical questionnaire is exposed in sinistre detail."""
        from app.models.souscription import Souscription
        from app.models.questionnaire import Questionnaire
        from app.core.enums import StatutSouscription
        
        product = test_product(db, code="SOS-MED-001", cout=Decimal("120.00"))
        subscription = Souscription(
            user_id=test_user.id,
            produit_assurance_id=product.id,
            numero_souscription="SUB-MED-001",
            prix_applique=product.cout,
            date_debut=datetime.utcnow() - timedelta(days=1),
            date_fin=datetime.utcnow() + timedelta(days=20),
            statut=StatutSouscription.ACTIVE
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        questionnaire = Questionnaire(
            souscription_id=subscription.id,
            type_questionnaire="medical",
            version=1,
            reponses={"allergies": "aucune", "traitement": "ibuprofène"},
            statut="complete"
        )
        db.add(questionnaire)
        db.commit()
        db.refresh(questionnaire)
        
        sos_response = client.post(
            "/api/v1/sos/trigger",
            json={
                "souscription_id": subscription.id,
                "latitude": PARIS_LAT,
                "longitude": PARIS_LON,
                "adresse": "Test medical dossier",
                "description": "Emergency with dossier",
                "priorite": "haute"
            },
            headers=auth_headers
        )
        assert sos_response.status_code == status.HTTP_201_CREATED
        alerte_id = sos_response.json()["id"]
        
        detail_response = client.get(
            f"/api/v1/sos/{alerte_id}/sinistre",
            headers=auth_headers
        )
        assert detail_response.status_code == status.HTTP_200_OK
        sinistre_detail = detail_response.json()
        medical_questionnaire = sinistre_detail.get("medical_questionnaire")
        assert medical_questionnaire is not None
        assert medical_questionnaire["id"] == questionnaire.id
        assert medical_questionnaire["type_questionnaire"] == "medical"

