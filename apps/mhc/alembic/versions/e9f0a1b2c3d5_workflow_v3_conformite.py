"""Workflow MyMHC V3 — conformité : sécurité des comptes, paramètres, demandes
d'informations (48 h), SOS sans géolocalisation, réclamations, demandes de
modification du profil, enfants bénéficiaires.

Revision ID: e9f0a1b2c3d5
Revises: d7e8f9a0b1c3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e9f0a1b2c3d5"
down_revision: Union[str, Sequence[str], None] = "d7e8f9a0b1c3"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


_USER_COLUMNS = [
    sa.Column("adresse", sa.Text(), nullable=True),
    sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("locked_until", sa.DateTime(), nullable=True),
    sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("last_device_id", sa.String(length=128), nullable=True),
    sa.Column("langue", sa.String(length=5), nullable=False, server_default="fr"),
    sa.Column("langue_documents", sa.String(length=5), nullable=False, server_default="fr"),
    sa.Column("notifications_non_essentielles", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("deleted_at", sa.DateTime(), nullable=True),
]

_SOUSCRIPTION_COLUMNS = [
    sa.Column("info_demandee_at", sa.DateTime(), nullable=True),
    sa.Column("info_demandee_message", sa.Text(), nullable=True),
    sa.Column("info_demandee_par", sa.Integer(), nullable=True),
    sa.Column("info_rappel_envoye_at", sa.DateTime(), nullable=True),
    sa.Column("info_reponse", sa.Text(), nullable=True),
    sa.Column("info_reponse_at", sa.DateTime(), nullable=True),
]


def upgrade() -> None:
    existing = _columns("users")
    with op.batch_alter_table("users") as batch:
        for column in _USER_COLUMNS:
            if column.name not in existing:
                batch.add_column(column)

    existing = _columns("souscriptions")
    with op.batch_alter_table("souscriptions") as batch:
        for column in _SOUSCRIPTION_COLUMNS:
            if column.name not in existing:
                batch.add_column(column)
        if "info_demandee_par" not in existing:
            batch.create_foreign_key(
                "fk_souscriptions_info_demandee_par", "users", ["info_demandee_par"], ["id"], ondelete="SET NULL"
            )
            batch.create_index("ix_souscriptions_info_demandee_at", ["info_demandee_at"])

    with op.batch_alter_table("alertes") as batch:
        batch.alter_column("latitude", existing_type=sa.Numeric(10, 8), nullable=True)
        batch.alter_column("longitude", existing_type=sa.Numeric(11, 8), nullable=True)

    tables = _tables()
    if "reclamations" not in tables:
        op.create_table(
            "reclamations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("reference", sa.String(length=40), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("categorie", sa.String(length=40), nullable=False),
            sa.Column("objet", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("souscription_id", sa.Integer(), sa.ForeignKey("souscriptions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("personne_concernee", sa.String(length=200), nullable=True),
            sa.Column("pieces_jointes", sa.JSON(), nullable=True),
            sa.Column("coordonnees", sa.JSON(), nullable=True),
            sa.Column("statut", sa.String(length=30), nullable=False, server_default="recue"),
            sa.Column("reponse", sa.Text(), nullable=True),
            sa.Column("complexe", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("parent_id", sa.Integer(), sa.ForeignKey("reclamations.id", ondelete="SET NULL"), nullable=True),
            sa.Column("assigned_to_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("echeance_premiere_reponse", sa.DateTime(), nullable=True),
            sa.Column("echeance_resolution", sa.DateTime(), nullable=True),
            sa.Column("premiere_reponse_at", sa.DateTime(), nullable=True),
            sa.Column("traitee_at", sa.DateTime(), nullable=True),
            sa.Column("cloturee_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_reclamations_id", "reclamations", ["id"])
        op.create_index("ix_reclamations_reference", "reclamations", ["reference"], unique=True)
        op.create_index("ix_reclamations_user_id", "reclamations", ["user_id"])
        op.create_index("ix_reclamations_categorie", "reclamations", ["categorie"])
        op.create_index("ix_reclamations_statut", "reclamations", ["statut"])
        op.create_index("ix_reclamations_souscription_id", "reclamations", ["souscription_id"])
        op.create_index("ix_reclamations_parent_id", "reclamations", ["parent_id"])

    if "reclamation_events" not in tables:
        op.create_table(
            "reclamation_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("reclamation_id", sa.Integer(), sa.ForeignKey("reclamations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("auteur_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("type_event", sa.String(length=30), nullable=False),
            sa.Column("statut", sa.String(length=30), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("visible_assure", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_reclamation_events_id", "reclamation_events", ["id"])
        op.create_index("ix_reclamation_events_reclamation_id", "reclamation_events", ["reclamation_id"])

    if "profile_change_requests" not in tables:
        op.create_table(
            "profile_change_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("champs", sa.JSON(), nullable=False),
            sa.Column("anciennes_valeurs", sa.JSON(), nullable=True),
            sa.Column("piece_identite", sa.JSON(), nullable=True),
            sa.Column("statut", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("motif_refus", sa.Text(), nullable=True),
            sa.Column("decided_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_profile_change_requests_id", "profile_change_requests", ["id"])
        op.create_index("ix_profile_change_requests_user_id", "profile_change_requests", ["user_id"])
        op.create_index("ix_profile_change_requests_statut", "profile_change_requests", ["statut"])

    if "enfants_beneficiaires" not in tables:
        op.create_table(
            "enfants_beneficiaires",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("parent_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("nom", sa.String(length=120), nullable=False),
            sa.Column("prenom", sa.String(length=120), nullable=True),
            sa.Column("date_naissance", sa.Date(), nullable=False),
            sa.Column("nationalite", sa.String(length=100), nullable=True),
            sa.Column("numero_piece", sa.String(length=60), nullable=True),
            sa.Column("validite_piece", sa.Date(), nullable=True),
            sa.Column("lien_parente", sa.String(length=50), nullable=True),
            sa.Column("photo", sa.Text(), nullable=True),
            sa.Column("copie_piece", sa.Text(), nullable=True),
            sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_enfants_beneficiaires_id", "enfants_beneficiaires", ["id"])
        op.create_index("ix_enfants_beneficiaires_parent_id", "enfants_beneficiaires", ["parent_id"])


def downgrade() -> None:
    op.drop_table("enfants_beneficiaires")
    op.drop_table("profile_change_requests")
    op.drop_table("reclamation_events")
    op.drop_table("reclamations")
    with op.batch_alter_table("souscriptions") as batch:
        batch.drop_index("ix_souscriptions_info_demandee_at")
        batch.drop_constraint("fk_souscriptions_info_demandee_par", type_="foreignkey")
        for column in reversed(_SOUSCRIPTION_COLUMNS):
            batch.drop_column(column.name)
    with op.batch_alter_table("users") as batch:
        for column in reversed(_USER_COLUMNS):
            batch.drop_column(column.name)
