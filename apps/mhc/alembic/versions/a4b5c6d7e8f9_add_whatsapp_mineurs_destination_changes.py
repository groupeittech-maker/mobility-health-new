"""Kit MyMHC : numéro WhatsApp, mineurs structurés, demandes de changement de destination.

Revision ID: a4b5c6d7e8f9
Revises: a9b0c1d2e3f4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users.numero_whatsapp — canal de vérification WhatsApp (kit MyMHC)
    op.add_column(
        "users",
        sa.Column("numero_whatsapp", sa.String(length=20), nullable=True),
    )

    # projets_voyage.mineurs — enfants mineurs assurés en données structurées
    op.add_column(
        "projets_voyage",
        sa.Column("mineurs", sa.JSON(), nullable=True),
    )

    # destination_change_requests — demandes validées par l'assureur
    op.create_table(
        "destination_change_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("souscription_id", sa.Integer(), nullable=False),
        sa.Column("projet_voyage_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ancienne_destination", sa.String(length=200), nullable=True),
        sa.Column("destination_country_id", sa.Integer(), nullable=True),
        sa.Column("nouvelle_destination", sa.String(length=200), nullable=False),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column("billet_document_id", sa.Integer(), nullable=True),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="en_attente"),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_by_id", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["souscription_id"], ["souscriptions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["projet_voyage_id"], ["projets_voyage.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["destination_country_id"], ["destination_countries.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["billet_document_id"], ["projet_voyage_documents.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_destination_change_requests_souscription_id",
        "destination_change_requests",
        ["souscription_id"],
    )
    op.create_index(
        "ix_destination_change_requests_projet_voyage_id",
        "destination_change_requests",
        ["projet_voyage_id"],
    )
    op.create_index(
        "ix_destination_change_requests_user_id",
        "destination_change_requests",
        ["user_id"],
    )
    op.create_index(
        "ix_destination_change_requests_statut",
        "destination_change_requests",
        ["statut"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_destination_change_requests_statut", table_name="destination_change_requests"
    )
    op.drop_index(
        "ix_destination_change_requests_user_id", table_name="destination_change_requests"
    )
    op.drop_index(
        "ix_destination_change_requests_projet_voyage_id",
        table_name="destination_change_requests",
    )
    op.drop_index(
        "ix_destination_change_requests_souscription_id",
        table_name="destination_change_requests",
    )
    op.drop_table("destination_change_requests")
    op.drop_column("projets_voyage", "mineurs")
    op.drop_column("users", "numero_whatsapp")
