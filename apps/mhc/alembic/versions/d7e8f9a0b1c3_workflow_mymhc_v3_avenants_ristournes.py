"""Workflow MyMHC V3 : avenants modification/prorogation, ristournes, fraude client.

Fusionne également les trois têtes existantes (photo de profil / invoice_items /
médecin-conseil par ville).

Revision ID: d7e8f9a0b1c3
Revises: b5c6d7e8f9a0, c6d7e8f9a1b2, e8f9a0b1c2d4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e8f9a0b1c3"
down_revision: Union[str, Sequence[str], None] = (
    "b5c6d7e8f9a0",
    "c6d7e8f9a1b2",
    "e8f9a0b1c2d4",
)
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _columns(table: str) -> set[str]:
    return {c["name"] for c in _inspector().get_columns(table)}


_AVENANT_COLUMNS = [
    sa.Column("date_debut_initiale", sa.DateTime(), nullable=True),
    sa.Column("date_fin_initiale", sa.DateTime(), nullable=True),
    sa.Column("nouvelle_date_debut", sa.DateTime(), nullable=True),
    sa.Column("nouvelle_date_fin", sa.DateTime(), nullable=True),
    sa.Column("montant_ajustement", sa.Numeric(12, 2), nullable=True),
    sa.Column("nature_ajustement", sa.String(length=20), nullable=True),
    sa.Column("paiement_id", sa.Integer(), nullable=True),
]


def upgrade() -> None:
    existing = _columns("avenants")
    with op.batch_alter_table("avenants") as batch:
        batch.alter_column("statut", type_=sa.String(length=30), existing_type=sa.String(length=20))
        for column in _AVENANT_COLUMNS:
            if column.name not in existing:
                batch.add_column(column)
        if "paiement_id" not in existing:
            batch.create_foreign_key(
                "fk_avenants_paiement_id", "paiements", ["paiement_id"], ["id"], ondelete="SET NULL"
            )
            batch.create_index("ix_avenants_paiement_id", ["paiement_id"])

    user_columns = _columns("users")
    with op.batch_alter_table("users") as batch:
        if "fraude_signalee" not in user_columns:
            batch.add_column(sa.Column("fraude_signalee", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "fraude_motif" not in user_columns:
            batch.add_column(sa.Column("fraude_motif", sa.Text(), nullable=True))

    if "ristournes" not in _inspector().get_table_names():
        op.create_table(
            "ristournes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("souscription_id", sa.Integer(), nullable=False),
            sa.Column("avenant_id", sa.Integer(), nullable=True),
            sa.Column("paiement_id", sa.Integer(), nullable=True),
            sa.Column("numero", sa.String(length=120), nullable=True),
            sa.Column("statut", sa.String(length=20), nullable=False, server_default="a_rembourser"),
            sa.Column("motif", sa.Text(), nullable=True),
            sa.Column("montant_prime", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("montant_frais_police", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("montant_taxes", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("montant_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("devise", sa.String(length=10), nullable=False, server_default="XAF"),
            sa.Column("moyen_remboursement", sa.String(length=30), nullable=True),
            sa.Column("reference_remboursement", sa.String(length=200), nullable=True),
            sa.Column("confirmed_by_id", sa.Integer(), nullable=True),
            sa.Column("confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["souscription_id"], ["souscriptions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["avenant_id"], ["avenants.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["paiement_id"], ["paiements.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["confirmed_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ristournes_id", "ristournes", ["id"])
        op.create_index("ix_ristournes_souscription_id", "ristournes", ["souscription_id"])
        op.create_index("ix_ristournes_avenant_id", "ristournes", ["avenant_id"])
        op.create_index("ix_ristournes_paiement_id", "ristournes", ["paiement_id"])
        op.create_index("ix_ristournes_numero", "ristournes", ["numero"], unique=True)
        op.create_index("ix_ristournes_statut", "ristournes", ["statut"])


def downgrade() -> None:
    op.drop_table("ristournes")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("fraude_motif")
        batch.drop_column("fraude_signalee")
    with op.batch_alter_table("avenants") as batch:
        batch.drop_index("ix_avenants_paiement_id")
        batch.drop_constraint("fk_avenants_paiement_id", type_="foreignkey")
        for column in reversed(_AVENANT_COLUMNS):
            batch.drop_column(column.name)
        batch.alter_column("statut", type_=sa.String(length=20), existing_type=sa.String(length=30))
