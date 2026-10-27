"""Conformité au « Workflow fonctionnel MyMHC V3 » : sécurité des comptes, paramètres,
demandes d'informations 48 h, expiration, mineurs, SOS, réclamations, profil, enfants."""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import status

from app.core.config import settings
from app.core.enums import Role, StatutSouscription
from app.core.security import get_password_hash
from app.models.attestation import Attestation
from app.models.souscription import Souscription
from app.models.user import User

PASSWORD = "testpassword123"


@pytest.fixture(autouse=True)
def _no_notifications(monkeypatch):
    from app.services.notification_service import NotificationService

    sent = []
    monkeypatch.setattr(NotificationService, "create_notification", staticmethod(lambda **kw: sent.append(kw)))
    return sent


def _login(client, username="testuser", password=PASSWORD, device="device-A"):
    return client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
        headers={"X-Device-Id": device},
    )


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _subscription(db, user, test_product, *, statut=StatutSouscription.ACTIVE, start=-1, end=20, code="V3"):
    product = test_product(db, code=f"V3-{code}-{datetime.utcnow().timestamp()}", cout=Decimal("100"))
    sous = Souscription(
        user_id=user.id,
        produit_assurance_id=product.id,
        numero_souscription=f"SUB-V3-{code}-{int(datetime.utcnow().timestamp() * 1000)}",
        prix_applique=Decimal("100"),
        date_debut=datetime.utcnow() + timedelta(days=start),
        date_fin=datetime.utcnow() + timedelta(days=end),
        statut=statut,
    )
    db.add(sous)
    db.commit()
    db.refresh(sous)
    return sous


# ---------------------------------------------------------------------------
# §3.2 / §3.3 Sécurité et profil
# ---------------------------------------------------------------------------
class TestAccountSecurity:
    def test_user_cannot_escalate_role_or_edit_identity(self, client, test_user, auth_headers, db):
        r = client.put(f"/api/v1/users/{test_user.id}", json={"role": "admin"}, headers=auth_headers)
        assert r.status_code == status.HTTP_403_FORBIDDEN
        r = client.put(f"/api/v1/users/{test_user.id}", json={"full_name": "Autre Nom"}, headers=auth_headers)
        assert r.status_code == status.HTTP_403_FORBIDDEN
        r = client.put(f"/api/v1/users/{test_user.id}", json={"contact_urgence": "+237600000000"}, headers=auth_headers)
        assert r.status_code == status.HTTP_200_OK
        db.refresh(test_user)
        assert test_user.role == Role.USER and test_user.full_name == "Test User"

    def test_lockout_after_five_wrong_passwords(self, client, test_user, db):
        for _ in range(settings.LOGIN_MAX_ATTEMPTS - 1):
            assert _login(client, password="mauvais").status_code == status.HTTP_401_UNAUTHORIZED
        r = _login(client, password="mauvais")
        assert r.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Mot de passe oublié" in r.json()["detail"]
        # Même le bon mot de passe est refusé pendant le blocage.
        assert _login(client).status_code == status.HTTP_429_TOO_MANY_REQUESTS
        test_user.locked_until = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
        assert _login(client).status_code == status.HTTP_200_OK

    def test_new_device_closes_previous_session(self, client, test_user):
        first = _login(client, device="phone-1").json()
        assert client.get("/api/v1/auth/me", headers=_auth(first["access_token"])).status_code == 200
        second = _login(client, device="phone-2").json()
        assert client.get("/api/v1/auth/me", headers=_auth(first["access_token"])).status_code == 401
        assert client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401
        assert client.get("/api/v1/auth/me", headers=_auth(second["access_token"])).status_code == 200

    def test_same_device_keeps_session(self, client, test_user):
        first = _login(client, device="phone-1").json()
        _login(client, device="phone-1")
        assert client.get("/api/v1/auth/me", headers=_auth(first["access_token"])).status_code == 200

    def test_change_password_requires_current_and_confirmation(self, client, test_user):
        token = _login(client).json()["access_token"]
        base = {"current_password": "faux", "new_password": "NouveauPass123", "confirm_password": "NouveauPass123"}
        assert client.post("/api/v1/auth/change-password", json=base, headers=_auth(token)).status_code == 400
        mismatch = {**base, "current_password": PASSWORD, "confirm_password": "Autre123456"}
        assert client.post("/api/v1/auth/change-password", json=mismatch, headers=_auth(token)).status_code == 400
        ok = client.post("/api/v1/auth/change-password", json={**base, "current_password": PASSWORD}, headers=_auth(token))
        assert ok.status_code == 200, ok.text
        assert client.get("/api/v1/auth/me", headers=_auth(token)).status_code == 401
        assert client.get("/api/v1/auth/me", headers=_auth(ok.json()["access_token"])).status_code == 200
        assert _login(client, password="NouveauPass123").status_code == 200

    def test_revoke_all_sessions(self, client, test_user):
        token = _login(client).json()["access_token"]
        assert client.post("/api/v1/auth/sessions/revoke-all", headers=_auth(token)).status_code == 200
        assert client.get("/api/v1/auth/me", headers=_auth(token)).status_code == 401

    def test_account_deletion_keeps_active_insurance(self, client, test_user, test_product, db):
        sous = _subscription(db, test_user, test_product)
        token = _login(client).json()["access_token"]
        bad = client.request("DELETE", "/api/v1/users/me", json={"password": PASSWORD, "confirmation": "oui"}, headers=_auth(token))
        assert bad.status_code == 400
        r = client.request("DELETE", "/api/v1/users/me", json={"password": PASSWORD, "confirmation": "SUPPRIMER"}, headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["assurances_actives"] == 1
        db.refresh(test_user)
        db.refresh(sous)
        assert test_user.is_active is False and test_user.deleted_at is not None
        assert sous.statut == StatutSouscription.ACTIVE

    def test_duplicate_email_suggests_login_or_recovery(self, client, test_user):
        r = client.post("/api/v1/auth/register", json={"email": test_user.email, "password": "Password123"})
        assert r.status_code == 400
        assert "Mot de passe oublié" in r.json()["detail"]

    def test_settings_languages(self, client, auth_headers):
        r = client.put("/api/v1/users/me/settings", json={"langue": "ar", "notifications_non_essentielles": False}, headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["langue"] == "ar" and r.json()["notifications_non_essentielles"] is False
        assert set(r.json()["langues_disponibles"]) == {"fr", "en", "es", "pt", "ar"}
        assert client.put("/api/v1/users/me/settings", json={"langue": "de"}, headers=auth_headers).status_code == 400

    def test_address_updated_directly(self, client, auth_headers, db, test_user):
        r = client.put("/api/v1/users/me/address", json={"adresse": "12 rue de la Paix, Douala"}, headers=auth_headers)
        assert r.status_code == 200
        db.refresh(test_user)
        assert test_user.adresse == "12 rue de la Paix, Douala"


class TestProfileChangeRequests:
    DOC = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

    def test_identity_change_requires_document_and_mhc_validation(self, client, auth_headers, admin_headers, db, test_user):
        r = client.post("/api/v1/profile-change-requests", json={"champs": {"full_name": "Jean Nouveau"}}, headers=auth_headers)
        assert r.status_code == 400
        r = client.post(
            "/api/v1/profile-change-requests",
            json={"champs": {"full_name": "Jean Nouveau", "nationalite": "Gabonaise"}, "piece_identite_data_url": self.DOC},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        request_id = r.json()["id"]
        # En attente : anciennes données conservées, pas de seconde demande.
        db.refresh(test_user)
        assert test_user.full_name == "Test User"
        again = client.post("/api/v1/profile-change-requests", json={"champs": {"nationalite": "X"}}, headers=auth_headers)
        assert again.status_code == 400
        assert client.post(f"/api/v1/profile-change-requests/{request_id}/decision", json={"approved": True}, headers=auth_headers).status_code == 403

        pending = client.get("/api/v1/profile-change-requests", headers=admin_headers).json()
        assert [p["id"] for p in pending] == [request_id]
        r = client.post(f"/api/v1/profile-change-requests/{request_id}/decision", json={"approved": True}, headers=admin_headers)
        assert r.status_code == 200, r.text
        db.refresh(test_user)
        assert test_user.full_name == "Jean Nouveau" and test_user.nationalite == "Gabonaise"

    def test_rejection_keeps_old_data_with_reason(self, client, auth_headers, admin_headers, db, test_user):
        r = client.post("/api/v1/profile-change-requests", json={"champs": {"pays_residence": "Gabon"}}, headers=auth_headers)
        assert r.status_code == 201, r.text
        request_id = r.json()["id"]
        assert client.post(f"/api/v1/profile-change-requests/{request_id}/decision", json={"approved": False}, headers=admin_headers).status_code == 400
        r = client.post(
            f"/api/v1/profile-change-requests/{request_id}/decision",
            json={"approved": False, "motif": "Justificatif illisible"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        db.refresh(test_user)
        assert test_user.pays_residence == "Cameroun"
        mine = client.get("/api/v1/profile-change-requests/me", headers=auth_headers).json()
        assert mine[0]["statut"] == "rejected" and mine[0]["motif_refus"] == "Justificatif illisible"


class TestChildren:
    def test_children_profiles_crud_and_age_limit(self, client, auth_headers):
        adult = (datetime.utcnow() - timedelta(days=19 * 365)).date().isoformat()
        r = client.post("/api/v1/users/me/enfants", json={"nom": "Grand", "date_naissance": adult}, headers=auth_headers)
        assert r.status_code == 400
        born = (datetime.utcnow() - timedelta(days=8 * 365)).date().isoformat()
        r = client.post(
            "/api/v1/users/me/enfants",
            json={"nom": "Petit", "prenom": "Léo", "date_naissance": born, "numero_piece": "AB123456"},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        child = r.json()
        assert child["numero_piece_masque"].endswith("456") and "AB1" not in child["numero_piece_masque"]
        assert [c["id"] for c in client.get("/api/v1/users/me/enfants", headers=auth_headers).json()] == [child["id"]]
        assert client.delete(f"/api/v1/users/me/enfants/{child['id']}", headers=auth_headers).status_code == 204
        assert client.get("/api/v1/users/me/enfants", headers=auth_headers).json() == []

    def test_minor_must_be_under_18_in_trip(self, client, auth_headers):
        depart = datetime.utcnow() + timedelta(days=10)
        adult_dob = (depart - timedelta(days=18 * 366)).date().isoformat()
        body = {
            "titre": "Famille", "destination": "Paris", "date_depart": depart.isoformat(),
            "date_retour": (depart + timedelta(days=10)).isoformat(),
            "notes": "Pays de résidence: Cameroun\nPays de destination: France",
            "mineurs": [{"nom": "Ado", "date_naissance": adult_dob}],
        }
        r = client.post("/api/v1/voyages/", json=body, headers=auth_headers)
        assert r.status_code == 400
        assert "moins de 18 ans" in r.json()["detail"]

    def test_pregnancy_over_five_months_for_child_rejected(self):
        from app.services.medical_eligibility import MedicalEligibilityError, validate_medical_eligibility

        with pytest.raises(MedicalEligibilityError):
            validate_medical_eligibility({"enceinte": "non", "enfants": [{"nom": "A", "reponses": {"enceinte": "oui", "mois_grossesse": 6}}]})


# ---------------------------------------------------------------------------
# §4.2 Demandes d'informations, §5 expiration, §8.2 notifications
# ---------------------------------------------------------------------------
class TestSubscriptionLifecycle:
    def test_info_request_reminder_then_auto_reject(self, client, db, test_user, test_product, admin_headers, auth_headers, _no_notifications):
        from app.services.subscription_lifecycle import process_info_requests

        sous = _subscription(db, test_user, test_product, statut=StatutSouscription.EN_ATTENTE_VALIDATION, start=10, end=20)
        sous.validation_medicale = "pending"
        db.commit()
        doctor = User(email="doc@x.com", username="docv3", hashed_password=get_password_hash("x12345678"),
                      role=Role.MEDICAL_REVIEWER, is_active=True)
        db.add(doctor)
        db.commit()
        token = client.post("/api/v1/auth/login", data={"username": "docv3", "password": "x12345678"}).json()["access_token"]
        r = client.post(f"/api/v1/admin/subscriptions/{sous.id}/request-info",
                        json={"message": "Merci de préciser votre traitement"}, headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["info_demandee_message"] == "Merci de préciser votre traitement"
        preview = [n for n in _no_notifications if n["type_notification"] == "souscription_info_requested"][0]
        assert "traitement" not in preview["message"]  # pas de détail médical dans l'aperçu

        db.refresh(sous)
        start = sous.info_demandee_at
        assert process_info_requests(db, now=start + timedelta(hours=settings.INFO_REQUEST_REMINDER_HOURS + 1)) == {"reminders": 1, "rejected": 0}
        assert process_info_requests(db, now=start + timedelta(hours=settings.INFO_REQUEST_DELAY_HOURS + 1)) == {"reminders": 0, "rejected": 1}
        db.refresh(sous)
        assert sous.statut == StatutSouscription.REFUSEE
        assert "48 h" in sous.validation_finale_notes and sous.validation_finale_date is not None

    def test_info_response_stops_timeout(self, client, db, test_user, test_product, auth_headers):
        from app.services.subscription_lifecycle import process_info_requests, request_info

        sous = _subscription(db, test_user, test_product, statut=StatutSouscription.EN_ATTENTE_VALIDATION, start=10, end=20)
        request_info(db, sous, "Précisez", reviewer_id=test_user.id)
        r = client.post(f"/api/v1/subscriptions/{sous.id}/info-response", json={"reponse": "Voici"}, headers=auth_headers)
        assert r.status_code == 200, r.text
        assert process_info_requests(db, now=datetime.utcnow() + timedelta(hours=72))["rejected"] == 0
        db.refresh(sous)
        assert sous.statut == StatutSouscription.EN_ATTENTE_VALIDATION

    def test_ended_policies_expire(self, db, test_user, test_product):
        from app.services.subscription_lifecycle import expire_ended_policies

        ended = _subscription(db, test_user, test_product, start=-20, end=-2, code="END")
        current = _subscription(db, test_user, test_product, start=-5, end=0, code="CUR")
        assert expire_ended_policies(db) == 1
        db.refresh(ended)
        db.refresh(current)
        assert ended.statut == StatutSouscription.EXPIREE
        assert current.statut == StatutSouscription.ACTIVE  # le dernier jour reste couvert

    def test_auto_reject_notification_has_no_medical_detail(self, db, test_user, test_product, _no_notifications):
        from app.models.questionnaire import Questionnaire
        from app.services.subscription_decision_service import SubscriptionDecisionEngine

        sous = _subscription(db, test_user, test_product, statut=StatutSouscription.EN_ATTENTE, start=10, end=20)
        db.add(Questionnaire(souscription_id=sous.id, type_questionnaire="medical", version=1,
                             reponses={"enceinte": "oui", "mois_grossesse": 7}, statut="complete"))
        db.commit()
        result = SubscriptionDecisionEngine.evaluate(db, sous)
        assert result.decision == "reject"
        note = [n for n in _no_notifications if n["type_notification"] == "souscription_decision_result"][0]
        assert "grossesse" not in note["message"].lower()
        assert "motif" in note["message"].lower()

    def test_documents_hidden_one_year_after_end(self, client, db, test_user, test_product, auth_headers):
        old = _subscription(db, test_user, test_product, statut=StatutSouscription.EXPIREE, start=-500, end=-400, code="OLD")
        recent = _subscription(db, test_user, test_product, start=-5, end=10, code="NEW")
        for sous in (old, recent):
            db.add(Attestation(souscription_id=sous.id, type_attestation="definitive",
                               numero_attestation=f"ATT-{sous.id}", chemin_fichier_minio="INLINE_PDF",
                               bucket_minio="inline", est_valide=True))
        db.commit()
        r = client.get("/api/v1/users/me/attestations", headers=auth_headers)
        assert [a["souscription_id"] for a in r.json()] == [recent.id]


# ---------------------------------------------------------------------------
# §7 Assistance
# ---------------------------------------------------------------------------
class TestSos:
    def _with_attestation(self, db, sous):
        db.add(Attestation(souscription_id=sous.id, type_attestation="definitive", numero_attestation=f"ATT-SOS-{sous.id}",
                           chemin_fichier_minio="INLINE_PDF", bucket_minio="inline", est_valide=True))
        db.commit()

    def test_sos_without_geolocation_uses_manual_address(self, client, db, test_user, test_product, test_hospital, auth_headers):
        sous = _subscription(db, test_user, test_product)
        self._with_attestation(db, sous)
        r = client.post("/api/v1/sos/trigger", json={"souscription_id": sous.id, "adresse": "Hôtel du Lac, Yaoundé"}, headers=auth_headers)
        assert r.status_code == 201, r.text
        assert r.json()["latitude"] is None and r.json()["adresse"] == "Hôtel du Lac, Yaoundé"

    def test_sos_blocked_before_effective_date(self, client, db, test_user, test_product, auth_headers):
        sous = _subscription(db, test_user, test_product, start=5, end=20)
        self._with_attestation(db, sous)
        r = client.post("/api/v1/sos/trigger", json={"souscription_id": sous.id, "latitude": 3.8, "longitude": 11.5}, headers=auth_headers)
        assert r.status_code == 400
        assert "pas encore commencé" in r.json()["detail"]


# ---------------------------------------------------------------------------
# §8.1 Réclamations
# ---------------------------------------------------------------------------
class TestReclamations:
    def test_full_lifecycle_and_contestation(self, client, auth_headers, admin_headers, test_user):
        meta = client.get("/api/v1/reclamations/categories").json()
        assert {c["code"] for c in meta["categories"]} == {
            "qualite_service", "etablissement_partenaire", "decision_couverture",
            "paiement_remboursement", "application", "autre",
        }
        assert "SOS" in meta["urgence_medicale"]
        assert client.post("/api/v1/reclamations", json={"categorie": "autre", "objet": "", "description": "x"}, headers=auth_headers).status_code == 400

        r = client.post("/api/v1/reclamations", json={"categorie": "paiement_remboursement", "objet": "Double débit",
                                                       "description": "J'ai été débité deux fois."}, headers=auth_headers)
        assert r.status_code == 201, r.text
        rec = r.json()
        assert rec["reference"].startswith("REC-") and rec["statut"] == "recue"
        assert rec["coordonnees"]["email"] == test_user.email
        assert rec["echeance_premiere_reponse"] and rec["echeance_resolution"]

        base = f"/api/v1/reclamations/{rec['id']}"
        assert client.post(base + "/statut", json={"statut": "en_analyse"}, headers=auth_headers).status_code == 403
        assert client.post(base + "/statut", json={"statut": "cloturee"}, headers=admin_headers).status_code == 400
        assert client.post(base + "/statut", json={"statut": "infos_requises"}, headers=admin_headers).status_code == 400
        r = client.post(base + "/statut", json={"statut": "infos_requises", "message": "Relevé bancaire ?"}, headers=admin_headers)
        assert r.status_code == 200
        r = client.post(base + "/messages", json={"message": "Relevé joint"}, headers=auth_headers)
        assert r.json()["statut"] == "en_analyse"
        assert client.post(base + "/contestation", json={"message": "Trop tôt"}, headers=auth_headers).status_code == 400
        r = client.post(base + "/statut", json={"statut": "traitee", "message": "Remboursement du doublon effectué."}, headers=admin_headers)
        assert r.json()["reponse"] == "Remboursement du doublon effectué."
        r = client.post(base + "/statut", json={"statut": "cloturee"}, headers=admin_headers)
        assert r.json()["statut"] == "cloturee"

        r = client.post(base + "/contestation", json={"message": "Montant incomplet"}, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["parent_id"] == rec["id"]
        mine = client.get("/api/v1/reclamations", headers=auth_headers).json()
        assert len(mine) == 2
        detail = client.get(base, headers=auth_headers).json()
        assert [e["statut"] for e in detail["historique"] if e["type"] == "statut"] == ["infos_requises", "en_analyse", "traitee", "cloturee"]
