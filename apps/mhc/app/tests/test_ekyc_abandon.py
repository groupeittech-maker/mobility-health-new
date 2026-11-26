"""Relance eKYC puis abandon à 2 h des souscriptions « en attente » (workflow V3)."""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.enums import StatutSouscription
from app.models.ekyc_session import EkycSession
from app.models.notification import Notification
from app.models.souscription import Souscription
from app.services import ekyc_abandon

NOW = datetime(2026, 11, 26, 10, 0)
_SEQ = {"n": 0}
_RECORDED_AT = {"t": None}


@pytest.fixture
def notifications(monkeypatch, db):
    """Capture l'appel au service — la dédup s'appuie sur la table notifications."""
    from app.services.notification_service import NotificationService

    sent = []

    def _record(**kw):
        sent.append(kw)
        db.add(Notification(
            user_id=kw["user_id"],
            type_notification=kw["type_notification"],
            titre=kw["titre"],
            message=kw["message"],
            lien_relation_id=kw.get("lien_relation_id"),
            lien_relation_type=kw.get("lien_relation_type"),
        ))
        db.commit()
        if _RECORDED_AT["t"] is not None:
            db.query(Notification).order_by(Notification.id.desc()).first().created_at = _RECORDED_AT["t"]
            db.commit()

    monkeypatch.setattr(NotificationService, "create_notification", staticmethod(_record))
    return sent


def _sous(db, user, test_product, *, statut=StatutSouscription.EN_ATTENTE):
    _SEQ["n"] += 1
    product = test_product(db, code=f"EKA-{_SEQ['n']}")
    sous = Souscription(
        user_id=user.id,
        produit_assurance_id=product.id,
        numero_souscription=f"EKA-{_SEQ['n']}",
        prix_applique=Decimal("100"),
        date_debut=NOW + timedelta(days=5),
        date_fin=NOW + timedelta(days=15),
        statut=statut,
    )
    db.add(sous)
    db.flush()
    sous.created_at = sous.updated_at = NOW - timedelta(hours=3)
    db.commit()
    return sous


def _session(db, sous, user, *, status, updated_at=None, expires_at=None):
    _SEQ["n"] += 1
    session = EkycSession(
        session_id=f"KYC-T-{_SEQ['n']}",
        customer_reference=f"C-{_SEQ['n']}",
        user_id=user.id,
        souscription_id=sous.id,
        status=status,
        expires_at=expires_at,
    )
    db.add(session)
    db.flush()
    session.created_at = session.updated_at = updated_at or NOW - timedelta(hours=1)
    db.commit()
    return session


class TestRelance:
    def test_dead_session_notifies_client_once(self, db, test_user, test_product, notifications):
        sous = _sous(db, test_user, test_product)
        _session(db, sous, test_user, status="EXPIRED", updated_at=NOW - timedelta(minutes=30))

        _RECORDED_AT["t"] = NOW
        report = ekyc_abandon.process_ekyc_abandons(db, now=NOW)
        assert report["relances"] == 1
        assert notifications[0]["type_notification"] == "ekyc_relance"
        assert "Relancez" in notifications[0]["message"]

        # Second scan : pas de doublon tant qu'aucune nouvelle session n'est morte.
        _RECORDED_AT["t"] = NOW + timedelta(minutes=15)
        report2 = ekyc_abandon.process_ekyc_abandons(db, now=NOW + timedelta(minutes=15))
        assert report2["relances"] == 0 and len(notifications) == 1

    def test_new_dead_session_renotifies(self, db, test_user, test_product, notifications):
        sous = _sous(db, test_user, test_product)
        _session(db, sous, test_user, status="REJECTED", updated_at=NOW - timedelta(minutes=40))
        _RECORDED_AT["t"] = NOW
        ekyc_abandon.process_ekyc_abandons(db, now=NOW)
        assert len(notifications) == 1

        _session(db, sous, test_user, status="EXPIRED", updated_at=NOW + timedelta(minutes=30))
        _RECORDED_AT["t"] = NOW + timedelta(minutes=35)
        report = ekyc_abandon.process_ekyc_abandons(db, now=NOW + timedelta(minutes=35))
        assert report["relances"] == 1 and len(notifications) == 2

    def test_live_session_no_notification(self, db, test_user, test_product, notifications):
        sous = _sous(db, test_user, test_product)
        _session(
            db, sous, test_user, status="IN_PROGRESS",
            updated_at=NOW - timedelta(minutes=5), expires_at=NOW + timedelta(minutes=25),
        )
        report = ekyc_abandon.process_ekyc_abandons(db, now=NOW)
        assert report["relances"] == 0 and report["abandonnees"] == 0 and not notifications


class TestRappel:
    def test_reminder_30_min_before_deadline(self, db, test_user, test_product, notifications):
        sous = _sous(db, test_user, test_product)
        _session(db, sous, test_user, status="EXPIRED", updated_at=NOW - timedelta(minutes=95))

        _RECORDED_AT["t"] = NOW
        report = ekyc_abandon.process_ekyc_abandons(db, now=NOW)
        assert report["rappels"] == 1
        assert notifications[0]["type_notification"] == "ekyc_relance_echeance"

        _RECORDED_AT["t"] = NOW + timedelta(minutes=10)
        report2 = ekyc_abandon.process_ekyc_abandons(db, now=NOW + timedelta(minutes=10))
        assert report2["rappels"] == 0 and len(notifications) == 1


class TestAbandon:
    def test_expires_after_2h_and_blocks(self, db, test_user, test_product, notifications):
        sous = _sous(db, test_user, test_product)
        _session(db, sous, test_user, status="REJECTED", updated_at=NOW - timedelta(hours=2, minutes=1))

        _RECORDED_AT["t"] = NOW
        report = ekyc_abandon.process_ekyc_abandons(db, now=NOW)
        assert report["abandonnees"] == 1
        db.expire_all()
        assert db.get(Souscription, sous.id).statut == StatutSouscription.EXPIREE
        assert notifications[0]["type_notification"] == "ekyc_abandon"

    def test_no_session_uses_souscription_activity(self, db, test_user, test_product, notifications):
        sous = _sous(db, test_user, test_product)  # updated_at = NOW-3h dans la fixture
        _RECORDED_AT["t"] = NOW
        report = ekyc_abandon.process_ekyc_abandons(db, now=NOW)
        assert report["abandonnees"] == 1
        assert db.get(Souscription, sous.id).statut == StatutSouscription.EXPIREE

    def test_stale_live_session_counts_as_dead(self, db, test_user, test_product, notifications):
        """Session « en cours » jamais expirée côté plateforme et sans webhook :
        figée depuis plus de 2 h → le dossier est abandonné quand même."""
        sous = _sous(db, test_user, test_product)
        _session(
            db, sous, test_user, status="IN_PROGRESS",
            updated_at=NOW - timedelta(hours=3), expires_at=None,
        )
        _RECORDED_AT["t"] = NOW
        report = ekyc_abandon.process_ekyc_abandons(db, now=NOW)
        assert report["abandonnees"] == 1

    def test_untouched_statuses_skipped(self, db, test_user, test_product, notifications):
        for statut in (StatutSouscription.EN_ATTENTE_PAIEMENT, StatutSouscription.ACTIVE,
                       StatutSouscription.EN_ATTENTE_VALIDATION):
            sous = _sous(db, test_user, test_product, statut=statut)
            _session(db, sous, test_user, status="EXPIRED", updated_at=NOW - timedelta(hours=5))
        report = ekyc_abandon.process_ekyc_abandons(db, now=NOW)
        assert report["abandonnees"] == 0 and report["relances"] == 0 and not notifications


class TestBlocking:
    def test_expired_souscription_cannot_create_session(self, client, db, test_user, test_product, auth_headers):
        sous = _sous(db, test_user, test_product)
        sous.statut = StatutSouscription.EXPIREE
        db.commit()

        r = client.post(
            "/api/v1/ekyc/sessions",
            json={"souscription_id": sous.id},
            headers=auth_headers,
        )
        assert r.status_code == 409
        assert "expiré" in r.json()["detail"]
