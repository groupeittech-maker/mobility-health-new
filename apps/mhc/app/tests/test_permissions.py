"""Tests de la matrice de permissions Edition/Contrôle/Consultation."""
from app.core.permissions import (
    FEATURES,
    LEVEL_CONSULTATION,
    LEVEL_CONTROLE,
    LEVEL_EDITION,
    ROLE_PERMISSIONS,
    has_permission,
    permission_level,
    permissions_for_role,
)


def test_admin_has_everything_in_edition():
    perms = permissions_for_role("admin")
    assert len(perms) == len(FEATURES)
    assert all(v == LEVEL_EDITION for v in perms.values())


def test_user_has_no_backoffice_permission():
    assert permissions_for_role("user") == {}
    assert not has_permission("user", "production", LEVEL_CONSULTATION)


def test_controle_does_not_imply_edition():
    assert has_permission("agent_conformite_sinistre", "sinistres", LEVEL_CONTROLE)
    assert has_permission("agent_conformite_sinistre", "sinistres", LEVEL_CONSULTATION)
    assert not has_permission("agent_conformite_sinistre", "sinistres", LEVEL_EDITION)


def test_edition_implies_lower_levels():
    assert has_permission("superviseur_technique", "comptes_produits", LEVEL_EDITION)
    assert has_permission("superviseur_technique", "comptes_produits", LEVEL_CONSULTATION)


def test_medecin_conseil_validation_chain():
    # 1re validation : hospitalisation / rapport / facturation en contrôle.
    assert has_permission("medecin_referent_mh", "hospitalisation", LEVEL_CONTROLE)
    assert has_permission("medecin_referent_mh", "facturation_medicale", LEVEL_CONTROLE)
    assert has_permission("medecin_referent_mh", "alerte_sos", LEVEL_EDITION)


def test_affaires_medicales_second_validation():
    assert has_permission("superviseur_affaires_medicales", "facturation_medicale", LEVEL_CONTROLE)
    assert has_permission("superviseur_affaires_medicales", "comptes_tpa", LEVEL_EDITION)


def test_reassureur_readonly_except_production():
    assert has_permission("agent_verificateur_reassureur", "production", LEVEL_EDITION)
    assert has_permission("agent_verificateur_reassureur", "encaissement_quote_part_sinistre", LEVEL_CONSULTATION)
    assert not has_permission("agent_verificateur_reassureur", "paiement_sinistre", LEVEL_CONSULTATION)


def test_assistant_souscription_limited_to_production():
    assert has_permission("assistant_souscription", "production", LEVEL_EDITION)
    assert not has_permission("assistant_souscription", "sinistres", LEVEL_CONSULTATION)


def test_hospital_roles():
    assert has_permission("medecin_hopital", "bulletin_sortie", LEVEL_EDITION)
    assert has_permission("agent_reception_hopital", "alerte_sos", LEVEL_EDITION)
    assert has_permission("agent_comptable_hopital", "facturation_medicale", LEVEL_EDITION)
    assert not has_permission("agent_comptable_hopital", "prise_en_charge", LEVEL_CONSULTATION)


def test_unknown_role_falls_back_to_none():
    assert permission_level("role_inconnu", "production") == "none"
    assert not has_permission(None, "production", LEVEL_CONSULTATION)


def test_all_matrix_roles_have_labels():
    from app.core.permissions import ROLE_LABELS

    for role_key in ROLE_PERMISSIONS:
        assert role_key in ROLE_LABELS, f"Label manquant pour {role_key}"
    assert len(ROLE_LABELS) == len(ROLE_PERMISSIONS) + 1  # +1 pour 'admin'
